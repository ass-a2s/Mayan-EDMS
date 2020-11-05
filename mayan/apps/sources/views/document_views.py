import logging

from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
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
from ..literals import SOURCE_UNCOMPRESS_CHOICE_ASK, SOURCE_UNCOMPRESS_CHOICE_ALWAYS
#from ..tasks import task_source_handle_upload

from .base import UploadBaseView

__all__ = ('UploadBaseView', 'DocumentUploadInteractiveView')
logger = logging.getLogger(name=__name__)


class DocumentUploadInteractiveView(UploadBaseView):
    document_form = NewDocumentForm

    def dispatch(self, request, *args, **kwargs):
        self.subtemplates_list = []

        self.document_type = self.get_document_type()

        AccessControlList.objects.check_access(
            obj=self.document_type, permissions=(permission_document_create,),
            user=request.user
        )

        self.tab_links = UploadBaseView.get_active_tab_links()

        return super().dispatch(request, *args, **kwargs)

    def forms_valid(self, forms):
        source_backend_instance = self.source.get_backend_instance()


        '''
        if getattr(self.source.get_backend(), 'can_uncompress', False):
            if self.source.get_backend_data()['uncompress'] == SOURCE_UNCOMPRESS_CHOICE_ASK:
                expand = forms['source_form'].cleaned_data.get('expand')
            else:
                if self.source.get_backend_data()['uncompress'] == SOURCE_UNCOMPRESS_CHOICE_ALWAYS:
                    expand = True
                else:
                    expand = False
        else:
            expand = False
        '''

        '''
        try:
            uploaded_file = source_backend_instance.get_upload_file_object(
                form_data=forms['source_form'].cleaned_data
            )
        except SourceException as exception:
            messages.error(message=exception, request=self.request)
        else:
            shared_uploaded_file = SharedUploadedFile.objects.create(
                file=uploaded_file.file
            )

            #if hasattr(source_backend_instance, 'clean_up_upload_file'):
            try:
                source_backend_instance.clean_up_upload_file(
                    upload_file_object=uploaded_file
                )
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
                        'New document queued for upload and will be '
                        'available shortly.'
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
    '''
        try:
            source_backend_instance.process_document(
                document_type=self.document_type, forms=forms,
                request=self.request
            )
        except Exception as exception:
            message = _(
                'Error processing source document upload; '
                '%(exception)s'
            ) % {
                'exception': exception,
            }
            logger.critical(msg=message, exc_info=True)
            #raise type(exception)(message)
            if self.request.is_ajax():
                return JsonResponse(
                    data={'error': force_text(s=message)}, status=500
                )
            else:
                raise type(exception)(message)
        else:
            messages.success(
                message=_(
                    'New document queued for upload and will be '
                    'available shortly.'
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
        context.update(
            {
                'title': _(
                    'Upload a document of type "%(document_type)s" from '
                    'source: %(source)s'
                ) % {
                    'document_type': self.document_type,
                    'source': self.source.label
                }
            }
        )

        return context

    def get_document_type(self):
        return  get_object_or_404(
            klass=DocumentType, pk=self.request.GET.get(
                'document_type_id', self.request.POST.get('document_type_id')
            )
        )

    def get_form_extra_kwargs__document_form(self):
        return {
            'document_type': self.document_type,
        }

    def get_form_extra_kwargs__source_form(self):
        show_expand = self.source.get_backend_instance().kwargs.get(
            'uncompress'
        ) == SOURCE_UNCOMPRESS_CHOICE_ASK

        return {
            'source': self.source,
            'show_expand': show_expand,
        }
