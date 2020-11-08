import json
import logging

from django import forms
from django.apps import apps
from django.db import transaction
from django.utils.encoding import force_text
from django.utils.translation import ugettext, ugettext_lazy as _

from mayan.apps.documents.models.document_models import Document
from mayan.apps.documents.models.document_file_models import DocumentFile
from mayan.apps.documents.tasks import task_document_file_upload

from ..literals import (
    SOURCE_INTERACTIVE_UNCOMPRESS_CHOICES,
    SOURCE_UNCOMPRESS_CHOICE_ALWAYS, SOURCE_UNCOMPRESS_CHOICE_ASK
)
from ..tasks import task_process_document_upload

logger = logging.getLogger(name=__name__)


class SourceBackendPeriodicMixin:
    def _delete_periodic_task(self, pk=None):
        PeriodicTask = apps.get_model(
            app_label='django_celery_beat', model_name='PeriodicTask'
        )

        try:
            periodic_task = PeriodicTask.objects.get(
                name=self._get_periodic_task_name(pk=pk)
            )

            interval_instance = periodic_task.interval

            #TODO:Update to use the a queryset
            if tuple(interval_instance.periodictask_set.values_list('id', flat=True)) == (periodic_task.pk,):
                # Only delete the interval if nobody else is using it
                interval_instance.delete()
            else:
                periodic_task.delete()
        except PeriodicTask.DoesNotExist:
            logger.warning(
                'Tried to delete non existent periodic task "%s"',
                self._get_periodic_task_name(pk)
            )

    def _get_periodic_task_name(self, pk=None):
        return 'check_interval_source-%i' % (pk or self.pk)

    def check(self, test=False):
        try:
            self._check_source(test=test)
        except Exception as exception:
            self.get_model_instance().error_log.create(
                text='{}; {}'.format(
                    exception.__class__.__name__, exception
                )
            )
            raise
        else:
            self.get_model_instance().error_log.all().delete()

    def delete(self, *args, **kwargs):
        pk = self.pk
        with transaction.atomic():
            self._delete_periodic_task(pk=pk)

    def save(self):
        IntervalSchedule = apps.get_model(
            app_label='django_celery_beat', model_name='PeriodicTask'
        )
        PeriodicTask = apps.get_model(
            app_label='django_celery_beat', model_name='PeriodicTask'
        )

        new_source = not self.pk
        with transaction.atomic():
            if not new_source:
                self._delete_periodic_task()

            # Create a new interval or use an existing one
            interval_instance, created = IntervalSchedule.objects.get_or_create(
                every=self.interval, period='seconds'
            )

            PeriodicTask.objects.create(
                name=self._get_periodic_task_name(),
                interval=interval_instance,
                task='mayan.apps.sources.tasks.task_check_interval_source',
                kwargs=json.dumps(obj={'source_id': self.pk})
            )



class SourceBackendInteractiveMixin:
    is_interactive = True

    def get_user(self, request):
        if not request.user.is_anonymous:
            self.user = request.user
            self.user_id = request.user.pk
        else:
            self.user = None
            self.user_id = None

    def process_document_file(self, document, forms, request):
        shared_uploaded_file = self.get_shared_uploaded_file(forms=forms)
        self.get_user(request=request)

        DocumentFile.execute_pre_create_hooks(
            kwargs={
                'document': document,
                'shared_uploaded_file': shared_uploaded_file,
                'user': self.user
            }
        )

        kwargs = {
            'action': int(
                forms['document_form'].cleaned_data.get('action')
            ),
            'comment': forms['document_form'].cleaned_data.get('comment'),
            'document_id': document.pk,
            'shared_uploaded_file_id': shared_uploaded_file.pk,
            'user_id': self.user_id
        }

        kwargs.update(self.get_task_extra_kwargs())

        task_document_file_upload.apply_async(kwargs=kwargs)

    def process_document(self, document_type, forms, request):
        shared_uploaded_file = self.get_shared_uploaded_file(forms=forms)
        self.get_user(request=request)

        #source_backend_instance.clean_up_upload_file(
        #    upload_file_object=uploaded_file
        #)

        query_string = request.GET.copy()
        query_string.update(request.POST)

        Document.execute_pre_create_hooks(
            kwargs={
                'document_type': document_type,
                'user': self.user
            }
        )

        DocumentFile.execute_pre_create_hooks(
            kwargs={
                'document_type': document_type,
                'shared_uploaded_file': shared_uploaded_file,
                'user': self.user
            }
        )

        kwargs={
            'description': forms['document_form'].cleaned_data.get('description'),
            'document_type_id': document_type.pk,
            'label': forms['document_form'].get_final_label(
                filename=force_text(shared_uploaded_file)
            ),
            'language': forms['document_form'].cleaned_data.get('language'),
            'query_string': query_string.urlencode(),
            'shared_uploaded_file_id': shared_uploaded_file.pk,
            'source_id': self.model_instance_id,
            'user_id': self.user_id,
        }

        kwargs.update(self.get_task_extra_kwargs())

        task_process_document_upload.apply_async(kwargs=kwargs)


#class SourceBackendInteractiveCompressedMixin(SourceBackendInteractiveMixin):
class SourceBackendCompressedMixin:
    @classmethod
    def get_setup_form_schema(cls):
        result = super().get_setup_form_schema()

        result['fields'].update(
            {
                'uncompress': {
                    'label': _('Uncompress'),
                    'class': 'django.forms.ChoiceField', 'default': '',
                    'help_text': _(
                        'Whether to expand or not compressed archives.'
                    ), 'kwargs': {
                        'choices': SOURCE_INTERACTIVE_UNCOMPRESS_CHOICES,
                    }, 'required': True
                }
            }
        )
        result['field_order'] = ('uncompress',) + result['field_order']

        result['widgets'].update(
            {
                'uncompress': {
                    'class': 'django.forms.widgets.Select', 'kwargs': {
                        'attrs': {'class': 'select2'},
                    }
                }
            }
        )
        return result

    @classmethod
    def get_upload_form_class(cls):
        class CompressedSourceUploadForm(super().get_upload_form_class()):
            expand = forms.BooleanField(
                label=_('Expand compressed files'), required=False,
                help_text=ugettext(
                    'Upload a compressed file\'s contained files as '
                    'individual documents.'
                )
            )

            def __init__(self, *args, **kwargs):
                self.field_order = ['expand']
                super().__init__(*args, **kwargs)

        return CompressedSourceUploadForm

    def get_uncompress_field(self, forms):
        if self.kwargs['uncompress'] == SOURCE_UNCOMPRESS_CHOICE_ASK:
            self.expand = forms['source_form'].cleaned_data.get('expand')
        else:
            if self.kwargs['uncompress'] == SOURCE_UNCOMPRESS_CHOICE_ALWAYS:
                self.expand = True
            else:
                self.expand = False

    def process_document(self, **kwargs):#document_type, forms, request):
        self.get_uncompress_field(forms=kwargs['forms'])
        return super().process_document(**kwargs)
        #    document_type=document_type, forms=forms, request=request
        #)

    def process_document_file(self, **kwargs):
        self.get_uncompress_field(forms=kwargs['forms'])

        return super().process_document_file(**kwargs)
        #    document_type=document_type, forms=forms, request=request
        #)

    def get_task_extra_kwargs(self):
        return {'expand': self.expand}
