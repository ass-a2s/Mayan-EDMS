import itertools
import json
import logging

from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.encoding import force_bytes, force_text
from django.utils.translation import ugettext, ugettext_lazy as _

from mayan.apps.common.serialization import yaml_load
from mayan.apps.documents.models.document_models import Document
from mayan.apps.documents.models.document_type_models import DocumentType
from mayan.apps.documents.tasks import task_document_file_upload
from mayan.apps.metadata.api import set_bulk_metadata
from mayan.apps.metadata.models import MetadataType

from ..literals import (
    SOURCE_INTERACTIVE_UNCOMPRESS_CHOICES, SOURCE_UNCOMPRESS_CHOICE_ALWAYS,
    SOURCE_UNCOMPRESS_CHOICE_ASK, SOURCE_UNCOMPRESS_CHOICE_NEVER
)
from ..tasks import task_process_document_upload
from ..wizards import WizardStep

from .literals import (
    DEFAULT_EMAIL_METADATA_ATTACHMENT_NAME, DEFAULT_PERIOD_INTERVAL
)

logger = logging.getLogger(name=__name__)


class SourceBaseMixin:
    def callback(self, document_file, **kwargs):
        return

    def get_callback_kwargs(self):
        return {}

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

    #def get_query_string(self):
    #    return {}

    def get_task_extra_kwargs(self):
        return {}

    def get_user(self):
        return None

    def process_document_file(self, **kwargs):
        self.process_kwargs = kwargs

        self.shared_uploaded_file = self.get_shared_uploaded_file()

        document = self.get_document()
        user = self.get_user()

        #DocumentFile.execute_pre_create_hooks(
        #    kwargs={
        #        'document': document,
        #        'shared_uploaded_file': self.shared_uploaded_file,
        #        'user': user
        #    }
        #)

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
    '''
    def process_document(self, **kwargs):
        self.process_kwargs = kwargs

        self.shared_uploaded_file = self.get_shared_uploaded_file()

        if not self.shared_uploaded_file:
            return

        document_type = self.get_document_type()
        user = self.get_user()

        #Document.execute_pre_create_hooks(
        #    kwargs={
        #        'document_type': document_type,
        #        'user': user
        #    }
        #)

        #DocumentFile.execute_pre_create_hooks(
        #    kwargs={
        #        'document_type': document_type,
        #        'shared_uploaded_file': self.shared_uploaded_file,
        #        'user': user
        #    }
        #)

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
    '''
    def process_documents(self, **kwargs):
        self.process_kwargs = kwargs

        #self.shared_uploaded_files = self.get_shared_uploaded_files()

        for self.shared_uploaded_file in self.get_shared_uploaded_files() or ():
            document_type = self.get_document_type()
            user = self.get_user()

            if user:
                user_id = user.pk
            else:
                user_id = None

            kwargs = {
                'callback_kwargs': self.get_callback_kwargs(),
                'description': self.get_document_description(),
                'document_type_id': document_type.pk,
                'label': self.get_document_label(),
                'language': self.get_document_language(),
                #'query_string': query_string_encoded,
                'shared_uploaded_file_id': self.shared_uploaded_file.pk,
                'source_id': self.model_instance_id,
                'user_id': user_id,
            }
            kwargs.update(self.get_task_extra_kwargs())

            task_process_document_upload.apply_async(kwargs=kwargs)


class SourceBackendEmailMixin:
    @classmethod
    def get_setup_form_schema(cls):
        result = super().get_setup_form_schema()

        result['fields'].update(
            {
                'host': {
                    'class': 'django.forms.CharField',
                    'label': _('Host'),
                    'kwargs': {
                        'max_length': 128
                    },
                    'required': True
                },
                'ssl': {
                    'class': 'django.forms.BooleanField',
                    'default': True,
                    'label': _('SSL')
                },
                'port': {
                    'class': 'django.forms.IntegerField',
                    'help_text': _(
                        'Typical choices are 110 for POP3, 995 for POP3 '
                        'over SSL, 143 for IMAP, 993 for IMAP over SSL.'
                    ),
                    'kwargs': {
                        'min_value': 0
                    },
                    'label': _('Port'),
                    'required': True
                },
                'username': {
                    'class': 'django.forms.CharField',
                    'kargs': {
                        'max_length': 128,
                    },
                    'label': _('Username'),
                },
                'password': {
                    'class': 'django.forms.CharField',
                    'kargs': {
                        'max_length': 128,
                    },
                    'label': _('Password'),
                },
                'metadata_attachment_name': {
                    'class': 'django.forms.CharField',
                    'default': DEFAULT_EMAIL_METADATA_ATTACHMENT_NAME,
                    'help_text': _(
                        'Name of the attachment that will contains the metadata type '
                        'names and value pairs to be assigned to the rest of the '
                        'downloaded attachments.'
                    ),
                    'kargs': {
                        'max_length': 128,
                    },
                    'label': _('Metadata attachment name'),
                },
                'from_metadata_type_id': {
                    'blank': True,
                    'class': 'django.forms.ChoiceField',
                    'help_text': _(
                        'Select a metadata type to store the email\'s '
                        '"from" value. Must be a valid metadata type for '
                        'the document type selected previously.'
                    ),
                    'kwargs': {
                        'choices': itertools.chain(
                            [(None, '---------')],
                            [(instance.id, instance) for instance in MetadataType.objects.all()],
                        )
                    },
                    'label': _('From metadata type'),
                    'null': True,
                    'required': False
                },
                'subject_metadata_type_id': {
                    'blank': True,
                    'class': 'django.forms.ChoiceField',
                    'help_text': _(
                        'Select a metadata type to store the email\'s '
                        'subject value. Must be a valid metadata type for '
                        'the document type selected previously.'
                    ),
                    'kwargs': {
                        'choices': itertools.chain(
                            [(None, '---------')],
                            [(instance.id, instance) for instance in MetadataType.objects.all()],
                        )
                    },
                    'label': _('Subject metadata type'),
                    'null': True,
                    'required': False
                },
                'store_body': {
                    'class': 'django.forms.BooleanField',
                    'default': True,
                    'help_text': _(
                        'Store the body of the email as a text document.'
                    ),
                    'label': _('Store email body'),
                    'required': False
                }
            }
        )
        result['field_order'] = (
            'host', 'ssl', 'port', 'username', 'password',
            'metadata_attachment_name', 'from_metadata_type_id',
            'subject_metadata_type_id', 'store_body'
        ) + result['field_order']

        result['widgets'].update(
            {
                'password': {
                    'class': 'django.forms.widgets.PasswordInput', 'kwargs': {
                        'render_value': True
                    }
                },
                'from_metadata_type_id': {
                    'class': 'django.forms.widgets.Select', 'kwargs': {
                        'attrs': {'class': 'select2'},
                    }
                },
                'subject_metadata_type_id': {
                    'class': 'django.forms.widgets.Select', 'kwargs': {
                        'attrs': {'class': 'select2'},
                    }
                }
            }
        )

        return result

    @staticmethod
    def process_message(source, message):
        from flanker import mime

        metadata_dictionary = {}

        message = mime.from_string(string=force_bytes(s=message))

        #if source.from_metadata_type:
        #    metadata_dictionary[
        #        source.from_metadata_type.name
        #    ] = message.headers.get('From')

        #if source.subject_metadata_type:
        #    metadata_dictionary[
        #        source.subject_metadata_type.name
        #    ] = message.headers.get('Subject')

        document_ids, parts_metadata_dictionary = SourceBackendEmailMixin._process_message(
            source=source, message=message
        )

        metadata_dictionary.update(parts_metadata_dictionary)

        if metadata_dictionary:
            for document in Document.objects.filter(id__in=document_ids):
                set_bulk_metadata(
                    document=document,
                    metadata_dictionary=metadata_dictionary
                )

    @staticmethod
    def _process_message(source, message):
        counter = 1
        document_ids = []
        metadata_dictionary = {}

        # Messages are tree based, do nested processing of message parts until
        # a message with no children is found, then work out way up.
        if message.parts:
            for part in message.parts:
                part_document_ids, part_metadata_dictionary = SourceBackendEmailMixin._process_message(
                    source=source, message=part,
                )

                document_ids.extend(part_document_ids)
                metadata_dictionary.update(part_metadata_dictionary)
        else:
            # Treat inlines as attachments, both are extracted and saved as
            # documents
            if message.is_attachment() or message.is_inline():
                # Reject zero length attachments
                if len(message.body) == 0:
                    return document_ids, metadata_dictionary

                label = message.detected_file_name or 'attachment-{}'.format(counter)
                counter = counter + 1

                with ContentFile(content=message.body, name=label) as file_object:
                    if label == source.metadata_attachment_name:
                        metadata_dictionary = yaml_load(
                            stream=file_object.read()
                        )
                        logger.debug(
                            'Got metadata dictionary: %s',
                            metadata_dictionary
                        )
                    else:
                        documents = source.handle_upload(
                            document_type=source.document_type,
                            file_object=file_object, expand=(
                                source.uncompress == SOURCE_UNCOMPRESS_CHOICE_ALWAYS
                            )
                        )

                        for document in documents:
                            document_ids.append(document.pk)

            else:
                # If it is not an attachment then it should be a body message part.
                # Another option is to use message.is_body()
                if message.detected_content_type == 'text/html':
                    label = 'email_body.html'
                else:
                    label = 'email_body.txt'

                if source.store_body:
                    with ContentFile(content=force_bytes(message.body), name=label) as file_object:
                        documents = source.handle_upload(
                            document_type=source.document_type,
                            expand=SOURCE_UNCOMPRESS_CHOICE_NEVER,
                            file_object=file_object
                        )

                        for document in documents:
                            document_ids.append(document.pk)

        return document_ids, metadata_dictionary

    def clean(self):
        document_type = self.get_document_type()
        form_metadata_type = self.get_from_metadata_type()
        subject_metadata_type = self.get_subject_metadata_type()

        #if self.kwargs['from_metadata_type_id']:
        if form_metadata_type:
            #if self.kwargs['from_metadata_type'].pk not in self.kwargs['document_type'].metadata.values_list('metadata_type', flat=True):
            #if not self.get_document_type().metadata.filter(metadata_type==self.kwargs['from_metadata_type']).exist():
            if not document_type.metadata.filter(metadata_type=form_metadata_type).exist():
                raise ValidationError(
                    {
                        'from_metadata_type': _(
                            '"From" metadata type "%(metadata_type)s" is not '
                            'valid for the document type: %(document_type)s'
                        ) % {
                            #'metadata_type': self.get_from_metadata_type(),
                            'metadata_type': form_metadata_type,
                            'document_type': document_type
                        }
                    }
                )

        #if self.kwargs['subject_metadata_type_id']:
        if subject_metadata_type:
            #if self.kwargs['subject_metadata_type_id'] not in self.get_document_type().metadata.values('metadata_type'):
            if not document_type.metadata.filter(metadata_type=subject_metadata_type).exist():
                raise ValidationError(
                    {
                        'subject_metadata_type': _(
                            'Subject metadata type "%(metadata_type)s" is not '
                            'valid for the document type: %(document_type)s'
                        ) % {
                            #'metadata_type': self.get_subject_metadata_type(),
                            'metadata_type': subject_metadata_type,
                            'document_type': document_type
                        }
                    }
                )
    def get_from_metadata_type(self):
        try:
            return MetadataType.objects.get(
                pk=self.kwargs['from_metadata_type_id']
            )
        except MetadataType.DoesNotExist:
            return None

    def get_subject_metadata_type(self):
        try:
            return MetadataType.objects.get(
                pk=self.kwargs['subject_metadata_type_id']
            )
        except MetadataType.DoesNotExist:
            return None


class SourceBackendPeriodicMixin:
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
                    'default': DEFAULT_PERIOD_INTERVAL,
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

        result['widgets'].update(
            {
                'document_type_id': {
                    'class': 'django.forms.widgets.Select', 'kwargs': {
                        'attrs': {'class': 'select2'},
                    }
                }
            }
        )

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


class SourceBackendInteractiveMixin:
    is_interactive = True

    def callback(self, document_file, **kwargs):
        WizardStep.post_upload_process(
            document=document_file.document,
            query_string=kwargs.get('query_string', {})
        )

    def get_callback_kwargs(self):
        query_string = self.process_kwargs['request'].GET.copy()
        query_string.update(self.process_kwargs['request'].POST)

        #if query_string:
        #query_string_encoded = query_string.urlencode()
        #else:
        #    query_string_encoded = None

        if hasattr(query_string, 'urlencode'):
            query_string = query_string.urlencode

        return {
            'query_string': query_string
        }

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
