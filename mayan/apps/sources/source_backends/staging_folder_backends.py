import errno
import fcntl
import json
import logging
import os
from pathlib import Path
import subprocess

from django.apps import apps
from django.db import transaction
from django.urls import reverse
from django.utils.encoding import force_text
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from mayan.apps.appearance.classes import Icon
from mayan.apps.documents.models.document_models import Document
from mayan.apps.documents.models.document_file_models import DocumentFile
from mayan.apps.documents.models.document_type_models import DocumentType
from mayan.apps.common.serialization import yaml_load
from mayan.apps.common.validators import YAMLValidator
from mayan.apps.storage.models import SharedUploadedFile
from mayan.apps.storage.utils import TemporaryFile

from ..classes import (
    PseudoFile, SourceBackend, SourceUploadedFile, StagingFile
)
from ..exceptions import SourceException
from ..forms import (
    #SaneScannerUploadForm, StagingUploadForm, WebFormUploadFormHTML5
    StagingUploadForm, WebFormUploadFormHTML5
)
from ..literals import (
    DEFAULT_INTERVAL, SOURCE_INTERACTIVE_UNCOMPRESS_CHOICES,
    SOURCE_UNCOMPRESS_CHOICE_ALWAYS, SOURCE_UNCOMPRESS_CHOICE_ASK
)
from ..settings import setting_scanimage_path
from ..tasks import task_process_document_upload

from .mixins import SourceBackendInteractiveMixin

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


class SourceBackendStagingFolder(SourceBackendInteractiveMixin, SourceBackend):
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

    def get_form_upload_file_object(self, form_data):
        staging_file = self.get_file(
            encoded_filename=form_data['staging_file_id']
        )
        return SourceUploadedFile(
            source=self, file=staging_file.as_file(), extra_data=staging_file
        )

    def get_shared_uploaded_file(self, forms):
        uploaded_file = self.get_form_upload_file_object(
            form_data=forms['source_form'].cleaned_data
        )
        return SharedUploadedFile.objects.create(
            file=uploaded_file.file
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

    #def post_process_document_file(self):
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
