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


class SourceBackendWebForm(SourceBackendInteractiveMixin, SourceBackend):
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

    def get_form_upload_file_object(self, form_data):
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

    def get_shared_uploaded_file(self, forms):
        uploaded_file = self.get_form_upload_file_object(
            form_data=forms['source_form'].cleaned_data
        )
        return SharedUploadedFile.objects.create(
            file=uploaded_file.file
        )

    def get_user(self, request):
        if not request.user.is_anonymous:
            user = request.user
            user_id = request.user.pk
        else:
            user = None
            user_id = None

