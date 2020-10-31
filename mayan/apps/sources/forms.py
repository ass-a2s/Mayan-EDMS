import json
import logging

from django import forms
from django.db.models import Model
from django.db.models.query import QuerySet
from django.utils.encoding import force_text
from django.utils.translation import ugettext, ugettext_lazy as _

from mayan.apps.documents.forms.document_forms import DocumentForm
from mayan.apps.documents.literals import DOCUMENT_FILE_ACTION_PAGE_CHOICES
from mayan.apps.views.forms import DynamicModelForm

from .classes import SourceBackend
from .models import (
    IMAPEmail, POP3Email, SaneScanner, Source, StagingFolderSource,
    WebFormSource, WatchFolderSource
)

logger = logging.getLogger(name=__name__)


class NewDocumentForm(DocumentForm):
    class Meta(DocumentForm.Meta):
        exclude = ('label', 'description')


class NewFileForm(forms.Form):
    comment = forms.CharField(
        help_text=_('An optional comment to explain the upload.'),
        label=_('Comment'), required=False,
        widget=forms.widgets.Textarea(attrs={'rows': 4}),
    )
    action = forms.ChoiceField(
        choices=DOCUMENT_FILE_ACTION_PAGE_CHOICES, label=_('Action'),
        help_text=_(
            'The action to take in regards to the pages of the new file '
            'being uploaded.'
        )
    )


class UploadBaseForm(forms.Form):
    def __init__(self, *args, **kwargs):
        show_expand = kwargs.pop('show_expand', False)
        self.source = kwargs.pop('source')

        super().__init__(*args, **kwargs)

        if show_expand:
            self.fields['expand'] = forms.BooleanField(
                label=_('Expand compressed files'), required=False,
                help_text=ugettext(
                    'Upload a compressed file\'s contained files as '
                    'individual documents.'
                )
            )


class StagingUploadForm(UploadBaseForm):
    """
    Form that show all the files in the staging folder specified by the
    StagingFile class passed as 'cls' argument
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            self.fields['staging_file_id'].choices = [
                (
                    staging_file.encoded_filename, force_text(s=staging_file)
                ) for staging_file in self.source.get_backend_instance().get_files()
            ]
        except Exception as exception:
            logger.error('exception: %s', exception)

    staging_file_id = forms.ChoiceField(label=_('Staging file'))


class SourceBackendSelectionForm(forms.Form):
    backend = forms.ChoiceField(
        choices=(), help_text=_('The backend used to create the new source.'),
        label=_('Backend')
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['backend'].choices = SourceBackend.get_choices()


class SourceBackendDynamicForm(DynamicModelForm):
    class Meta:
        fields = ('label', 'enabled', 'backend_data')
        model = Source
        widgets = {'backend_data': forms.widgets.HiddenInput}

    def __init__(self, *args, **kwargs):
        #self.request = kwargs.pop('request')
        #self.backend_data = kwargs.pop('backend_data')

        super().__init__(*args, **kwargs)
        if self.instance.backend_data:
            backend_data = json.loads(s=self.instance.backend_data)
            for key in self.instance.get_backend().fields:
                self.fields[key].initial = backend_data.get(key)

            #for key, value in json.loads(s=self.instance.backend_data).items():
            #    self.fields[key].initial = value

    def clean(self):
        data = super().clean()

        # Consolidate the dynamic fields into a single JSON field called
        # 'backend_data'.
        backend_data = {}

        for field_name, field_data in self.schema['fields'].items():
            backend_data[field_name] = data.pop(
                field_name, field_data.get('default', None)
            )
            if isinstance(backend_data[field_name], QuerySet):
                # Flatten the queryset to a list of ids
                backend_data[field_name] = list(
                    backend_data[field_name].values_list('id', flat=True)
                )
            elif isinstance(backend_data[field_name], Model):
                # Store only the ID of a model instance
                backend_data[field_name] = backend_data[field_name].pk

        #data['backend_data'] = backend_data
        #data = import_string(dotted_path=self.action_path).clean(
        #    form_data=data, request=self.request
        #)
        data['backend_data'] = json.dumps(obj=backend_data)
        #data['backend_data'] = json.dumps(obj=backend_data)
        return data


#class WebFormUploadForm(UploadBaseForm):
#    file = forms.FileField(label=_('File'))


class WebFormUploadFormHTML5(UploadBaseForm):
    file = forms.FileField(
        label=_('File'), widget=forms.widgets.FileInput(
            attrs={'class': 'hidden', 'hidden': True}
        )
    )


class SaneScannerUploadForm(UploadBaseForm):
    pass


#class SaneScannerSetupForm(forms.ModelForm):
#    class Meta:
#        fields = (
#            'label', 'device_name', 'mode', 'resolution', 'source',
#            'adf_mode', 'enabled'
#        )
#        model = SaneScanner


#class WebFormSetupForm(forms.ModelForm):
#    class Meta:
#        fields = ('label', 'enabled', 'uncompress')
#        model = WebFormSource


#class StagingFolderSetupForm(forms.ModelForm):
#    class Meta:
#        fields = (
#            'label', 'enabled', 'folder_path', 'preview_width',
#            'preview_height', 'uncompress', 'delete_after_upload'
#        )
#        model = StagingFolderSource


#class EmailSetupBaseForm(forms.ModelForm):
#    class Meta:
#        fields = (
#            'label', 'enabled', 'interval', 'document_type', 'uncompress',
#            'host', 'ssl', 'port', 'username', 'password',
#            'metadata_attachment_name', 'subject_metadata_type',
#            'from_metadata_type', 'store_body'
#        )
#        widgets = {
#            'password': forms.widgets.PasswordInput(render_value=True)
#        }#


#class IMAPEmailSetupForm(EmailSetupBaseForm):
#    class Meta(EmailSetupBaseForm.Meta):
#        fields = EmailSetupBaseForm.Meta.fields + (
#            'mailbox', 'search_criteria', 'store_commands',
#            'mailbox_destination', 'execute_expunge'
#        )
#        model = IMAPEmail#


#class POP3EmailSetupForm(EmailSetupBaseForm):
#    class Meta(EmailSetupBaseForm.Meta):
#        fields = EmailSetupBaseForm.Meta.fields + ('timeout',)
#        model = POP3Email


#class WatchFolderSetupForm(forms.ModelForm):
#    class Meta:
#        fields = (
#            'label', 'enabled', 'interval', 'document_type', 'uncompress',
#            'folder_path', 'include_subdirectories'
#        )
#        model = WatchFolderSource
