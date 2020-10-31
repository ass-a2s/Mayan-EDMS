import logging

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from mayan.apps.acls.models import AccessControlList
from mayan.apps.documents.models import (
    DocumentType, Document, DocumentFile
)
from mayan.apps.documents.permissions import permission_document_create
from mayan.apps.storage.models import SharedUploadedFile

from ..exceptions import SourceException
from ..forms import NewDocumentForm
from ..literals import SOURCE_UNCOMPRESS_CHOICE_ASK, SOURCE_UNCOMPRESS_CHOICE_Y
from ..tasks import task_source_handle_upload

from .base import UploadBaseView

__all__ = ('UploadBaseView', 'DocumentUploadInteractiveView')
logger = logging.getLogger(name=__name__)


class DocumentUploadInteractiveView(UploadBaseView):
    def create_source_form_form(self, **kwargs):
        if hasattr(self.source, 'uncompress'):
            show_expand = self.source.uncompress == SOURCE_UNCOMPRESS_CHOICE_ASK
        else:
            show_expand = False

        return self.get_form_classes()['source_form'](
            prefix=kwargs['prefix'],
            source=self.source,
            show_expand=show_expand,
            data=kwargs.get('data', None),
            files=kwargs.get('files', None),
        )

    def create_document_form_form(self, **kwargs):
        return self.get_form_classes()['document_form'](
            prefix=kwargs['prefix'],
            document_type=self.document_type,
            data=kwargs.get('data', None),
            files=kwargs.get('files', None),
        )

    def dispatch(self, request, *args, **kwargs):
        self.subtemplates_list = []

        self.document_type = get_object_or_404(
            klass=DocumentType, pk=self.request.GET.get(
                'document_type_id', self.request.POST.get('document_type_id')
            )
        )

        AccessControlList.objects.check_access(
            obj=self.document_type, permissions=(permission_document_create,),
            user=request.user
        )

        self.tab_links = UploadBaseView.get_active_tab_links()

        return super().dispatch(request, *args, **kwargs)

    def forms_valid(self, forms):
        if getattr(self.source.get_backend(), 'can_compress', False):
            if self.source.get_backend_data()['uncompress'] == SOURCE_UNCOMPRESS_CHOICE_ASK:
                expand = forms['source_form'].cleaned_data.get('expand')
            else:
                if self.source.get_backend_data['uncompress'] == SOURCE_UNCOMPRESS_CHOICE_Y:
                    expand = True
                else:
                    expand = False
        else:
            expand = False

        try:
            uploaded_file = self.source.get_backend_instance().get_upload_file_object(
                form_data=forms['source_form'].cleaned_data
            )
        except SourceException as exception:
            messages.error(message=exception, request=self.request)
        else:
            shared_uploaded_file = SharedUploadedFile.objects.create(
                file=uploaded_file.file
            )

            try:
                self.source.clean_up_upload_file(uploaded_file)
            except Exception as exception:
                messages.error(message=exception, request=self.request)

            if not self.request.user.is_anonymous:
                user = self.request.user
                user_id = self.request.user.pk
            else:
                user = None
                user_id = None

            querystring = self.request.GET.copy()
            querystring.update(self.request.POST)

            try:
                Document.execute_pre_create_hooks(
                    kwargs={
                        'document_type': self.document_type,
                        'user': user
                    }
                )

                DocumentFile.execute_pre_create_hooks(
                    kwargs={
                        'document_type': self.document_type,
                        'shared_uploaded_file': shared_uploaded_file,
                        'user': user
                    }
                )

                task_source_handle_upload.apply_async(
                    kwargs={
                        'description': forms['document_form'].cleaned_data.get('description'),
                        'document_type_id': self.document_type.pk,
                        'expand': expand,
                        'label': forms['document_form'].get_final_label(
                            filename=force_text(shared_uploaded_file)
                        ),
                        'language': forms['document_form'].cleaned_data.get('language'),
                        'querystring': querystring.urlencode(),
                        'shared_uploaded_file_id': shared_uploaded_file.pk,
                        'source_id': self.source.pk,
                        'user_id': user_id,
                    }
                )
            except Exception as exception:
                message = _(
                    'Error executing document upload task; '
                    '%(exception)s'
                ) % {
                    'exception': exception,
                }
                logger.critical(msg=message, exc_info=True)
                raise type(exception)(message)
            else:
                messages.success(
                    message=_(
                        'New document queued for upload and will be available '
                        'shortly.'
                    ), request=self.request
                )

        return HttpResponseRedirect(
            redirect_to='{}?{}'.format(
                reverse(
                    viewname=self.request.resolver_match.view_name,
                    kwargs=self.request.resolver_match.kwargs
                ), self.request.META['QUERY_STRING']
            ),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _(
            'Upload a document of type "%(document_type)s" from '
            'source: %(source)s'
        ) % {'document_type': self.document_type, 'source': self.source.label}

        return context

    def get_form_classes(self):
        source_form_class = self.source.get_backend().upload_form_class

        return {
            'document_form': NewDocumentForm,
            'source_form': source_form_class
        }
