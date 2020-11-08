import json
import logging
import subprocess

from django.urls import reverse
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from mayan.apps.common.serialization import yaml_load
from mayan.apps.common.validators import YAMLValidator
from mayan.apps.storage.models import SharedUploadedFile

from ..classes import SourceBackend, SourceUploadedFile
from ..forms import WebFormUploadFormHTML5
from ..literals import SOURCE_INTERACTIVE_UNCOMPRESS_CHOICES

from .mixins import (
    SourceBackendCompressedMixin, SourceBackendInteractiveMixin
)

logger = logging.getLogger(name=__name__)


class SourceBackendWebForm(
    SourceBackendCompressedMixin, SourceBackendInteractiveMixin, SourceBackend
):
    label = _('Web form')
    upload_form_class = WebFormUploadFormHTML5

    def get_form_upload_file_object(self, form_data):
        return SourceUploadedFile(
            source=self.model_instance_id, file=form_data['file']
        )

    def get_view_context(self, context, request):
        return {
            'subtemplates_list': [
                {
                    'name': 'appearance/generic_multiform_subtemplate.html',
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
