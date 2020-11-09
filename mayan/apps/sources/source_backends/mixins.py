import json
import logging

from django import forms
from django.apps import apps
from django.db import transaction
from django.utils.encoding import force_text
from django.utils.translation import ugettext, ugettext_lazy as _

from mayan.apps.documents.models.document_models import Document
from mayan.apps.documents.models.document_file_models import DocumentFile
from mayan.apps.documents.models.document_type_models import DocumentType
from mayan.apps.documents.tasks import task_document_file_upload

from ..literals import (
    DEFAULT_INTERVAL, SOURCE_INTERACTIVE_UNCOMPRESS_CHOICES,
    SOURCE_UNCOMPRESS_CHOICE_ALWAYS, SOURCE_UNCOMPRESS_CHOICE_ASK
)

from ..tasks import task_process_document_upload

logger = logging.getLogger(name=__name__)


class SourceBaseMixin:
    def get_document(self):
        raise NotImplementedError

    def get_document_description(self):
        return None

    def get_document_file_action(self):
        return None

    def get_document_file_comment(self):
        return None

    def get_document_label(self):
        return None

    def get_document_language(self):
        return None

    def get_document_type(self):
        raise NotImplementedError

    def get_query_string(self):
        return {}

    def get_task_extra_kwargs(self):
        return {}

    def get_user(self):
        return None

    def process_document_file(self, **kwargs):
        self.process_kwargs = kwargs

        self.shared_uploaded_file = self.get_shared_uploaded_file()

        document = self.get_document()
        user = self.get_user()

        DocumentFile.execute_pre_create_hooks(
            kwargs={
                'document': document,
                'shared_uploaded_file': self.shared_uploaded_file,
                'user': user
            }
        )

        if user:
            user_id = user.pk
        else:
            user_id = None

        kwargs = {
            'action': self.get_document_file_action(),
            'comment': self.get_document_file_comment(),
            'document_id': document.pk,
            'shared_uploaded_file_id': self.shared_uploaded_file.pk,
            'user_id': user_id
        }

        kwargs.update(self.get_task_extra_kwargs())

        task_document_file_upload.apply_async(kwargs=kwargs)

    def process_document(self, **kwargs):
        self.process_kwargs = kwargs

        self.shared_uploaded_file = self.get_shared_uploaded_file()

        document_type = self.get_document_type()
        user = self.get_user()

        Document.execute_pre_create_hooks(
            kwargs={
                'document_type': document_type,
                'user': user
            }
        )

        DocumentFile.execute_pre_create_hooks(
            kwargs={
                'document_type': document_type,
                'shared_uploaded_file': self.shared_uploaded_file,
                'user': user
            }
        )

        if user:
            user_id = user.pk
        else:
            user_id = None

        query_string = self.get_query_string()

        if query_string:
            query_string_encoded = query_string.urlencode()
        else:
            query_string_encoded = None

        kwargs = {
            'description': self.get_document_description(),
            'document_type_id': document_type.pk,
            'label': self.get_document_label(),
            'language': self.get_document_language(),
            'query_string': query_string_encoded,
            'shared_uploaded_file_id': self.shared_uploaded_file.pk,
            'source_id': self.model_instance_id,
            'user_id': user_id,
        }
        kwargs.update(self.get_task_extra_kwargs())

        task_process_document_upload.apply_async(kwargs=kwargs)


class SourceBackendPeriodicMixin(SourceBaseMixin):
    @classmethod
    def get_setup_form_schema(cls):
        result = super().get_setup_form_schema()

        result['fields'].update(
            {
                'document_type_id': {
                    'class': 'django.forms.ChoiceField',
                    'default': '',
                    'help_text': _(
                        'Assign a document type to documents uploaded from this '
                        'source.'
                    ),
                    'kwargs': {
                        'choices': [(document_type.id, document_type) for document_type in DocumentType.objects.all()],
                    },
                    'label': _('Document type'),
                    'required': True
                },
                'interval': {
                    'class': 'django.forms.IntegerField',
                    'default': DEFAULT_INTERVAL,
                    'help_text': _(
                        'Interval in seconds between checks for new '
                        'documents.'
                    ),
                    'kwargs': {
                        'min_value': 0
                    },
                    'label': _('Interval'),
                    'required': True
                },
            }
        )
        result['field_order'] = ('document_type_id', 'interval',) + result['field_order']

        return result

    def get_document_type(self):
        return DocumentType.objects.get(pk=self.kwargs['document_type_id'])

    def delete(self, *args, **kwargs):
        pk = self.pk
        with transaction.atomic():
            self.delete_periodic_task(pk=pk)

    def delete_periodic_task(self, pk=None):
        PeriodicTask = apps.get_model(
            app_label='django_celery_beat', model_name='PeriodicTask'
        )

        try:
            periodic_task = PeriodicTask.objects.get(
                name=self.get_periodic_task_name(pk=pk)
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
                self.get_periodic_task_name(pk)
            )

    def get_periodic_task_name(self, pk=None):
        return 'check_interval_source-%i' % (pk or self.pk)

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
                self.delete_periodic_task()

            # Create a new interval or use an existing one
            interval_instance, created = IntervalSchedule.objects.get_or_create(
                every=self.interval, period='seconds'
            )

            PeriodicTask.objects.create(
                name=self.get_periodic_task_name(),
                interval=interval_instance,
                task='mayan.apps.sources.tasks.task_source_process_document',
                kwargs=json.dumps(obj={'source_id': self.pk})
            )


class SourceBackendInteractiveMixin(SourceBaseMixin):
    is_interactive = True

    def get_document(self):
        return self.process_kwargs['document']

    def get_document_description(self):
        return self.process_kwargs['forms']['document_form'].cleaned_data.get('description')

    def get_document_file_action(self):
        return int(self.process_kwargs['forms']['document_form'].cleaned_data.get('action'))

    def get_document_file_comment(self):
        return self.process_kwargs['forms']['document_form'].cleaned_data.get('comment')

    def get_document_label(self):
        return self.process_kwargs['forms']['document_form'].get_final_label(
            filename=force_text(self.shared_uploaded_file)
        )

    def get_document_language(self):
        return self.process_kwargs['forms']['document_form'].cleaned_data.get('language')

    def get_document_type(self):
        return self.process_kwargs['document_type']

    def get_query_string(self):
        query_string = self.process_kwargs['request'].GET.copy()
        query_string.update(self.process_kwargs['request'].POST)
        return query_string

    def get_user(self):
        if not self.process_kwargs['request'].user.is_anonymous:
            return self.process_kwargs['request'].user
        else:
            return None


class SourceBackendCompressedMixin:
    uncompress_choices = SOURCE_INTERACTIVE_UNCOMPRESS_CHOICES

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
                        'choices': cls.uncompress_choices,
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

    def get_expand(self):
        if self.kwargs['uncompress'] == SOURCE_UNCOMPRESS_CHOICE_ASK:
            return self.process_kwargs['forms']['source_form'].cleaned_data.get('expand')
        else:
            if self.kwargs['uncompress'] == SOURCE_UNCOMPRESS_CHOICE_ALWAYS:
                return True
            else:
                return False

    def get_task_extra_kwargs(self):
        return {'expand': self.get_expand()}
