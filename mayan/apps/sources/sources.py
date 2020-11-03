import errno
import fcntl
import logging
import os
from pathlib import Path
import subprocess

from django.contrib import messages

from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from mayan.apps.appearance.classes import Icon
from mayan.apps.documents.models.document_type_models import DocumentType
from mayan.apps.common.serialization import yaml_load
from mayan.apps.common.validators import YAMLValidator
from mayan.apps.storage.utils import TemporaryFile

from .classes import (
    PseudoFile, SourceBackend, SourceUploadedFile, StagingFile
)
from .exceptions import SourceException
from .forms import (
    #SaneScannerUploadForm, StagingUploadForm, WebFormUploadFormHTML5
    StagingUploadForm, WebFormUploadFormHTML5
)
from .literals import (
    DEFAULT_INTERVAL, SOURCE_INTERACTIVE_UNCOMPRESS_CHOICES,
    SOURCE_UNCOMPRESS_CHOICE_ALWAYS
)
from .settings import setting_scanimage_path

logger = logging.getLogger(name=__name__)


#interactive
#label, enabled, uncompress

#periodic
#label, enabled, uncompress, document type, interval


# webforms - interactive

# staging folders - interactive
# folder path, preview width, preview height, delete after upload

# SANE - interactive
# device name, mode, resolution, paper source, adf mode

# POP3 - periodic
# host, ssl, port, username, password, metadata attachment name,
# subject metadata, from metadata, store body, timeout

# IMAP - periodic
# host, ssl, port, username, password, metadata attachment name,
# subject metadata, from metadata, store body, timeout
# Mailbox, search criteria, store comands, destination mailbox, expunge.

# watchfolder - periodic
# folder path, include subdirectories


# ToDO: ACTION after upload
# - Delete
# - Move to folder


class SourceBackendIMAPEmail(SourceBackend):
    can_uncompress = True
    field_order = ('interval', 'uncompress',)
    fields = {
        'interval': {
            'class': 'django.forms.IntegerField',
            'default': DEFAULT_INTERVAL,
            'help_text': _(
                'Interval in seconds between checks for new documents.'
            ),
            'label': _('Interval'),
            'required': True
        },
        'uncompress': {
            'class': 'django.forms.ChoiceField', 'default': '',
            'help_text': _(
                'Whether to expand or not compressed archives.'
            ),
            'kwargs': {
                'choices': SOURCE_INTERACTIVE_UNCOMPRESS_CHOICES,
            },
            'label': _('Uncompress'),
            'required': True
        },
    }
    label = _('IMAP email')
    widgets = {
        'uncompress': {
            'class': 'django.forms.widgets.Select', 'kwargs': {
                'attrs': {'class': 'select2'},
            }
        }
    }
    '''
    host = models.CharField(max_length=128, verbose_name=_('Host'))
    ssl = models.BooleanField(default=True, verbose_name=_('SSL'))
    port = models.PositiveIntegerField(blank=True, null=True, help_text=_(
        'Typical choices are 110 for POP3, 995 for POP3 over SSL, 143 for '
        'IMAP, 993 for IMAP over SSL.'), verbose_name=_('Port')
    )
    username = models.CharField(max_length=96, verbose_name=_('Username'))
    password = models.CharField(max_length=96, verbose_name=_('Password'))
    metadata_attachment_name = models.CharField(
        default=DEFAULT_METADATA_ATTACHMENT_NAME,
        help_text=_(
            'Name of the attachment that will contains the metadata type '
            'names and value pairs to be assigned to the rest of the '
            'downloaded attachments.'
        ), max_length=128, verbose_name=_('Metadata attachment name')
    )
    subject_metadata_type = models.ForeignKey(
        blank=True, help_text=_(
            'Select a metadata type to store the email\'s subject value. '
            'Must be a valid metadata type for the document type selected '
            'previously.'
        ), on_delete=models.CASCADE, null=True, related_name='email_subject',
        to=MetadataType, verbose_name=_('Subject metadata type')
    )
    from_metadata_type = models.ForeignKey(
        blank=True, help_text=_(
            'Select a metadata type to store the email\'s "from" value. '
            'Must be a valid metadata type for the document type selected '
            'previously.'
        ), on_delete=models.CASCADE, null=True, related_name='email_from',
        to=MetadataType, verbose_name=_('From metadata type')
    )
    store_body = models.BooleanField(
        default=True, help_text=_(
            'Store the body of the email as a text document.'
        ), verbose_name=_('Store email body')
    )
    ###

    mailbox = models.CharField(
        default=DEFAULT_IMAP_MAILBOX,
        help_text=_('IMAP Mailbox from which to check for messages.'),
        max_length=64, verbose_name=_('Mailbox')
    )
    search_criteria = models.TextField(
        blank=True, default=DEFAULT_IMAP_SEARCH_CRITERIA, help_text=_(
            'Criteria to use when searching for messages to process. '
            'Use the format specified in '
            'https://tools.ietf.org/html/rfc2060.html#section-6.4.4'
        ), null=True, verbose_name=_('Search criteria')
    )
    store_commands = models.TextField(
        blank=True, default=DEFAULT_IMAP_STORE_COMMANDS, help_text=_(
            'IMAP STORE command to execute on messages after they are '
            'processed. One command per line. Use the commands specified in '
            'https://tools.ietf.org/html/rfc2060.html#section-6.4.6 or '
            'the custom commands for your IMAP server.'
        ), null=True, verbose_name=_('Store commands')
    )
    execute_expunge = models.BooleanField(
        default=True, help_text=_(
            'Execute the IMAP expunge command after processing each email '
            'message.'
        ), verbose_name=_('Execute expunge')
    )
    mailbox_destination = models.CharField(
        blank=True, help_text=_(
            'IMAP Mailbox to which processed messages will be copied.'
        ), max_length=96, null=True, verbose_name=_('Destination mailbox')
    )
    '''



class SourceBackendPOP3Email(SourceBackend):
    can_uncompress = True
    field_order = ('interval', 'uncompress',)
    fields = {
        'interval': {
            'class': 'django.forms.IntegerField',
            'default': DEFAULT_INTERVAL,
            'help_text': _(
                'Interval in seconds between checks for new documents.'
            ),
            'label': _('Interval'),
            'required': True
        },
        'uncompress': {
            'class': 'django.forms.ChoiceField', 'default': '',
            'help_text': _(
                'Whether to expand or not compressed archives.'
            ),
            'kwargs': {
                'choices': SOURCE_INTERACTIVE_UNCOMPRESS_CHOICES,
            },
            'label': _('Uncompress'),
            'required': True
        },
    }
    label = _('POP3 email')
    widgets = {
        'uncompress': {
            'class': 'django.forms.widgets.Select', 'kwargs': {
                'attrs': {'class': 'select2'},
            }
        }
    }


class SourceBackendSANEScanner(SourceBackend):
    can_uncompress = True
    field_order = ('device_name', 'arguments')
    fields = {
        'device_name': {
            'class': 'django.forms.CharField',
            'help_text': _(
                'Device name as returned by the SANE backend.'
            ),
            'kwargs': {'max_length': 255,},
            'label': _('Device name'),
            'required': True
        },
        'arguments': {
            'class': 'django.forms.CharField',
            'help_text': _(
                'YAML formatted arguments to pass to the `scanimage` '
                'command. The arguments will change depending on the '
                'device. Execute `scanimage --help --device-name=DEVICE` '
                'for the list of supported arguments.'
            ),
            'label': _('Arguments'),
            'required': False,
        },
    }
    is_interactive = True
    label = _('SANE Scanner')
    #upload_form_class = SaneScannerUploadForm
    widgets = {
        'arguments': {
            'class': 'django.forms.widgets.Textarea', 'kwargs': {
                'attrs': {
                    'rows': 10
                }
            }
        }
    }

    def execute_command(self, arguments):
        command_line = [
            setting_scanimage_path.value
        ]
        command_line.extend(arguments)

        with TemporaryFile() as stderr_file_object:
            stdout_file_object = TemporaryFile()

            try:
                logger.debug('Scan command line: %s', command_line)
                subprocess.check_call(
                    command_line, stdout=stdout_file_object,
                    stderr=stderr_file_object
                )
            except subprocess.CalledProcessError:
                stderr_file_object.seek(0)
                error_message = stderr_file_object.read()
                logger.error(
                    'Exception while executing scanning command for source:%s ; %s', self,
                    error_message
                )

                message = _(
                    'Error while executing scanning command '
                    '"%(command_line)s"; %(error_message)s'
                ) % {
                    'command_line': ' '.join(command_line),
                    'error_message': error_message
                }
                self.get_model_instance().error_log.create(text=message)
                raise SourceException(message)
            else:
                stdout_file_object.seek(0)
                self.get_model_instance().error_log.all().delete()
                return stdout_file_object

    def get_upload_file_object(self, form_data):
        arguments = [
            '-d', self.kwargs['device_name'], '--format', 'tiff',
        ]

        loaded_arguments = yaml_load(s=self.kwargs.get('arguments', '{}'))
        for item in loaded_arguments.items():
            arguments.extend(item)

        file_object = self.execute_command(arguments=arguments)

        return SourceUploadedFile(
            source=self, file=PseudoFile(
                file=file_object, name='scan {}'.format(now())
            )
        )

    def get_view_context(self, context, request):
        return {
            'subtemplates_list': [
                {
                    'name': 'sources/upload_multiform_subtemplate.html',
                    'context': {
                        'forms': context['forms'],
                        'is_multipart': True,
                        'title': _('Document properties'),
                        'submit_label': _('Scan'),
                    },
                }
            ]
        }


class SourceBackendStagingFolder(SourceBackend):
    can_uncompress = True
    field_order = (
        'uncompress', 'folder_path', 'preview_width', 'preview_height',
        'delete_after_upload'
    )
    fields = {
        'uncompress': {
            'class': 'django.forms.ChoiceField',
            'default': '',
            'help_text': _(
                'Whether to expand or not compressed archives.'
            ),
            'kwargs': {
                'choices': SOURCE_INTERACTIVE_UNCOMPRESS_CHOICES,
            },
            'label': _('Uncompress'),
            'required': True
        },
        'folder_path': {
            'class': 'django.forms.CharField',
            'default': '',
            'help_text': _(
                'Server side filesystem path.'
            ),
            'kwargs': {
                'max_length': 255,
            },
            'label': _('Folder path'),
            'required': True
        },
        'preview_width': {
            'class': 'django.forms.IntegerField',
            'help_text': _(
                'Width value to be passed to the converter backend.'
            ),
            'kwargs': {
                'min_value': 0
            },
            'label': _('Preview width'),
            'required': True
        },
        'preview_height': {
            'class': 'django.forms.IntegerField',
            'help_text': _(
                'Height value to be passed to the converter backend.'
            ),
            'kwargs': {
                'min_value': 0
            },
            'label': _('Preview height'),
            'required': False
        },
        'delete_after_upload': {
            'class': 'django.forms.BooleanField',
            'help_text': _(
                'Delete the file after is has been successfully uploaded.'
            ),
            'label': _('Delete after upload'),
            'required': False
        }
    }
    icon_staging_folder_file = Icon(driver_name='fontawesome', symbol='file')
    is_interactive = True
    label = _('Staging folder')
    upload_form_class = StagingUploadForm
    widgets = {
        'uncompress': {
            'class': 'django.forms.widgets.Select', 'kwargs': {
                'attrs': {'class': 'select2'},
            }
        }
    }

    def clean_up_upload_file(self, upload_file_object):
        if self.kwargs['delete_after_upload']:
            try:
                upload_file_object.extra_data.delete()
            except Exception as exception:
                logger.error(
                    'Error deleting staging file: %s; %s',
                    upload_file_object, exception
                )
                raise Exception(
                    _('Error deleting staging file; %s') % exception
                )

    def get_file(self, *args, **kwargs):
        return StagingFile(staging_folder=self, *args, **kwargs)

    def get_files(self):
        try:
            for entry in sorted([os.path.normcase(f) for f in os.listdir(self.kwargs['folder_path']) if os.path.isfile(os.path.join(self.kwargs['folder_path'], f))]):
                yield self.get_file(filename=entry)
        except OSError as exception:
            logger.error(
                'Unable get list of staging files from source: %s; %s',
                self, exception
            )
            raise Exception(
                _('Unable get list of staging files: %s') % exception
            )

    def get_upload_file_object(self, form_data):
        staging_file = self.get_file(
            encoded_filename=form_data['staging_file_id']
        )
        return SourceUploadedFile(
            source=self, file=staging_file.as_file(), extra_data=staging_file
        )

    def get_view_context(self, context, request):
        #staging_filelist = []

        #try:
        staging_filelist = list(self.get_files())

        #except Exception:# as exception:
        #    raise
        #    messages.error(message=exception, request=request)
        #finally:
        subtemplates_list = [
            {
                'name': 'appearance/generic_multiform_subtemplate.html',
                'context': {
                    'forms': context['forms'],
                },
            },
            {
                'name': 'appearance/generic_list_subtemplate.html',
                'context': {
                    'hide_link': True,
                    'no_results_icon': SourceBackendStagingFolder.icon_staging_folder_file,
                    'no_results_text': _(
                        'This could mean that the staging folder is '
                        'empty. It could also mean that the '
                        'operating system user account being used '
                        'for Mayan EDMS doesn\'t have the necessary '
                        'file system permissions for the folder.'
                    ),
                    'no_results_title': _(
                        'No staging files available'
                    ),
                    'object_list': staging_filelist,
                }
            },
        ]

        return {'subtemplates_list': subtemplates_list}


class SourceBackendMixinPeriodic:
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


class SourceBackendWatchFolder(SourceBackendMixinPeriodic, SourceBackend):
    can_uncompress = True
    field_order = (
        'uncompress', 'interval', 'document_type_id', 'folder_path',
        'include_subdirectories',
    )
    fields = {
        'uncompress': {
            'class': 'django.forms.ChoiceField',
            'default': '',
            'help_text': _(
                'Whether to expand or not compressed archives.'
            ),
            'kwargs': {
                'choices': SOURCE_INTERACTIVE_UNCOMPRESS_CHOICES,
            },
            'label': _('Uncompress'),
            'required': True
        },
        'interval': {
            'class': 'django.forms.IntegerField',
            'default': DEFAULT_INTERVAL,
            'help_text': _(
                'Interval in seconds between checks for new documents.'
            ),
            'kwargs': {
                'min_value': 0
            },
            'label': _('Interval'),
            'required': True
        },
        'folder_path': {
            'class': 'django.forms.CharField',
            'default': '',
            'help_text': _(
                'Server side filesystem path.'
            ),
            'kwargs': {
                'max_length': 255,
            },
            'label': _('Folder path'),
            'required': True
        },
        'include_subdirectories': {
            'class': 'django.forms.BooleanField',
            'default': '',
            'help_text': _(
                'If checked, not only will the folder path be scanned for '
                'files but also its subdirectories.'
            ),
            #'kwargs': {
            #    'max_length': 255,
            #},
            'label': _('Include subdirectories?'),
            'required': False
        },
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
        }
    }
    label = _('Watch folder')
    widgets = {
        'uncompress': {
            'class': 'django.forms.widgets.Select', 'kwargs': {
                'attrs': {'class': 'select2'},
            }
        }
    }

    def _check_source(self, test=False):
        path = Path(self.kwargs['folder_path'])
        # Force testing the path and raise errors for the log
        path.lstat()
        if not path.is_dir():
            raise SourceException('Path {} is not a directory.'.format(path))

        if self.kwargs['include_subdirectories']:
            iterator = path.rglob(pattern='*')
        else:
            iterator = path.glob(pattern='*')

        for entry in iterator:
            if entry.is_file() or entry.is_symlink():
                with entry.open(mode='rb+') as file_object:
                    try:
                        fcntl.lockf(file_object, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except IOError as exception:
                        if exception.errno != errno.EAGAIN:
                            raise
                    else:
                        self.get_model_instance().handle_upload(
                            file_object=file_object,
                            expand=(self.kwargs['uncompress'] == SOURCE_UNCOMPRESS_CHOICE_ALWAYS),
                            label=entry.name
                        )
                        if not test:
                            entry.unlink()


class SourceBackendWebForm(SourceBackend):
    can_uncompress = True
    field_order = ('uncompress',)
    fields = {
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
    is_interactive = True
    label = _('Web form')
    upload_form_class = WebFormUploadFormHTML5
    widgets = {
        'uncompress': {
            'class': 'django.forms.widgets.Select', 'kwargs': {
                'attrs': {'class': 'select2'},
            }
        }
    }

    def get_upload_file_object(self, form_data):
        return SourceUploadedFile(
            source=self.model_instance_id, file=form_data['file']
        )

    def get_view_context(self, context, request):
        return {
            'subtemplates_list': [
                {
                    'name': 'sources/upload_multiform_subtemplate.html',
                    'context': {
                        'forms': context['forms'],
                        'is_multipart': True,
                        'form_action': '{}?{}'.format(
                            reverse(
                                viewname=request.resolver_match.view_name,
                                kwargs=request.resolver_match.kwargs
                            ), request.META['QUERY_STRING']
                        ),
                        'form_css_classes': 'dropzone',
                        'form_disable_submit': True,
                        'form_id': 'html5upload',
                    },
                }
            ]
        }
