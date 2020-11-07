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

from .mixins import SourceBackendMixinPeriodic

logger = logging.getLogger(name=__name__)


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
