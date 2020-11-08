import errno
import json
import logging
import os
import subprocess

import sh

from django.apps import apps
from django.core.files import File
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
from mayan.apps.storage.utils import NamedTemporaryFile, TemporaryFile

from ..classes import PseudoFile, SourceBackend, SourceUploadedFile
from ..exceptions import SourceException
from ..settings import setting_scanimage_path

from .mixins import SourceBackendInteractiveMixin

logger = logging.getLogger(name=__name__)


#interactive
#label, enabled, uncompress

# SANE - interactive
# device name, mode, resolution, paper source, adf mode

# ToDO: ACTION after upload
# - Delete
# - Move to folder


class SourceBackendSANEScanner(SourceBackendInteractiveMixin, SourceBackend):
    can_uncompress = True
    field_order = ('device_name', 'arguments')
    fields = {
        'device_name': {
            'class': 'django.forms.CharField',
            'help_text': _(
                'Device name as returned by the SANE backend.'
            ),
            'kwargs': {'max_length': 255},
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
    widgets = {
        'arguments': {
            'class': 'django.forms.widgets.Textarea', 'kwargs': {
                'attrs': {
                    'rows': 10
                }
            }
        }
    }
    '''
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
    '''
    '''
    def get_form_upload_file_object(self, form_data):
        NamedTemporaryFile

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
    '''

    def get_shared_uploaded_file(self, forms):
        command_scanimage = sh.Command(path=setting_scanimage_path.value)

        with NamedTemporaryFile() as file_object:
            command_scanimage = command_scanimage.bake(
                device_name=self.kwargs['device_name'],
                format='tiff', output_file=file_object.name
            )
            command_scanimage()

            file_object.seek(0)

            return SharedUploadedFile.objects.create(
                file=File(file=file_object), filename='scan {}'.format(
                    now()
                )
            )


        #arguments = [
        #    '--device-name', self.kwargs['device_name'], '--format', 'tiff', '--output-file', 222
        #]
        #command_scanimage(device_name='epson2:net:192.168.11.50', format='tiff', output_file='/tmp/test')

        #uploaded_file = self.get_form_upload_file_object(
        #    form_data=forms['source_form'].cleaned_data
        #)
        #return SharedUploadedFile.objects.create(
        #    file=uploaded_file.file
        #)

    def get_view_context(self, context, request):
        return {
            'subtemplates_list': [
                {
                    'name': 'appearance/generic_multiform_subtemplate.html',
                    'context': {
                        'forms': context['forms'],
                        'is_multipart': True,
                        'title': _('Document properties'),
                        'submit_label': _('Scan'),
                    },
                }
            ]
        }
