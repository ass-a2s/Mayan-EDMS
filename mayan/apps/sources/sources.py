from django.utils.translation import ugettext_lazy as _

from .classes import SourceBackend, SourceUploadedFile
from .forms import (
    SaneScannerUploadForm, StagingUploadForm, WebFormUploadForm
)
from .literals import DEFAULT_INTERVAL, SOURCE_INTERACTIVE_UNCOMPRESS_CHOICES

#                POP3Email, IMAPEmail, StagingFolderSource, WatchFolderSource,
#                WebFormSource,

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

#def get_upload_form_class(source_type_name):
#    if source_type_name == SOURCE_CHOICE_WEB_FORM:
#        return WebFormUploadForm
#    elif source_type_name == SOURCE_CHOICE_STAGING:
#        return StagingUploadForm
#    elif source_type_name == SOURCE_CHOICE_SANE_SCANNER:
#        return SaneScannerUploadForm

class SourceBackendIMAPEmail(SourceBackend):
    can_compress = True
    field_order = ('interval', 'uncompress',)
    fields = {
        'interval': {
            'label': _('Interval'),
            'class': 'django.forms.IntegerField',
            'default': DEFAULT_INTERVAL,
            'help_text': _(
                'Interval in seconds between checks for new documents.'
            ), 'required': True
        },
        'uncompress': {
            'label': _('Uncompress'),
            'class': 'django.forms.ChoiceField', 'default': '',
            'help_text': _(
                'Whether to expand or not compressed archives.'
            ), 'kwargs': {
                'choices': SOURCE_INTERACTIVE_UNCOMPRESS_CHOICES,
            }, 'required': True
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


class SourceBackendSANEScanner(SourceBackend):
    field_order = ('device_name',)
    fields = {
        'device_name': {
            'label': _('Device name'),
            'class': 'django.forms.CharField', 'default': '',
            'help_text': _(
                'Device name as returned by the SANE backend.'
            ), 'kwargs': {
                'max_length': 255,
            }, 'required': True
        }
    }
    is_interactive = True
    label = _('SANE Scanner')
    upload_form_class = SaneScannerUploadForm
    #widgets = {
    #    'uncompress': {
    #        'class': 'django.forms.widgets.Select', 'kwargs': {
    #            'attrs': {'class': 'select2'},
    #        }
    #    }
    #}

    """
class SaneScanner(InteractiveSource):
    can_compress = False
    is_interactive = True
    source_type = SOURCE_CHOICE_SANE_SCANNER

    device_name = models.CharField(
        max_length=255,
        help_text=_('Device name as returned by the SANE backend.'),
        verbose_name=_('Device name')
    )
    mode = models.CharField(
        blank=True, choices=SCANNER_MODE_CHOICES, default=SCANNER_MODE_COLOR,
        help_text=_(
            'Selects the scan mode (e.g., lineart, monochrome, or color). '
            'If this option is not supported by your scanner, leave it blank.'
        ), max_length=16, verbose_name=_('Mode')
    )
    resolution = models.PositiveIntegerField(
        blank=True, null=True, help_text=_(
            'Sets the resolution of the scanned image in DPI (dots per inch). '
            'Typical value is 200. If this option is not supported by your '
            'scanner, leave it blank.'
        ), verbose_name=_('Resolution')
    )
    source = models.CharField(
        blank=True, choices=SCANNER_SOURCE_CHOICES, help_text=_(
            'Selects the scan source (such as a document-feeder). If this '
            'option is not supported by your scanner, leave it blank.'
        ), max_length=32, null=True, verbose_name=_('Paper source')
    )
    adf_mode = models.CharField(
        blank=True, choices=SCANNER_ADF_MODE_CHOICES,
        help_text=_(
            'Selects the document feeder mode (simplex/duplex). If this '
            'option is not supported by your scanner, leave it blank.'
        ), max_length=16, verbose_name=_('ADF mode')
    )
    """


class SourceBackendPOP3Email(SourceBackend):
    can_compress = True
    field_order = ('interval', 'uncompress',)
    fields = {
        'interval': {
            'label': _('Interval'),
            'class': 'django.forms.IntegerField',
            'default': DEFAULT_INTERVAL,
            'help_text': _(
                'Interval in seconds between checks for new documents.'
            ), 'required': True
        },
        'uncompress': {
            'label': _('Uncompress'),
            'class': 'django.forms.ChoiceField', 'default': '',
            'help_text': _(
                'Whether to expand or not compressed archives.'
            ), 'kwargs': {
                'choices': SOURCE_INTERACTIVE_UNCOMPRESS_CHOICES,
            }, 'required': True
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



class SourceBackendStagingFolder(SourceBackend):
    can_compress = True
    field_order = ('uncompress', 'folder_path')
    fields = {
        'uncompress': {
            'label': _('Uncompress'),
            'class': 'django.forms.ChoiceField', 'default': '',
            'help_text': _(
                'Whether to expand or not compressed archives.'
            ), 'kwargs': {
                'choices': SOURCE_INTERACTIVE_UNCOMPRESS_CHOICES,
            }, 'required': True
        },
        'folder_path': {
            'label': _('Folder path'),
            'class': 'django.forms.CharField', 'default': '',
            'help_text': _(
                'Server side filesystem path.'
            ), 'kwargs': {
                'max_length': 255,
            }, 'required': True
        }
    }
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
    '''
    folder_path = models.CharField(
        max_length=255, help_text=_('Server side filesystem path.'),
        verbose_name=_('Folder path')
    )
    preview_width = models.IntegerField(
        help_text=_('Width value to be passed to the converter backend.'),
        verbose_name=_('Preview width')
    )
    preview_height = models.IntegerField(
        blank=True, null=True,
        help_text=_('Height value to be passed to the converter backend.'),
        verbose_name=_('Preview height')
    )
    uncompress = models.CharField(
        choices=SOURCE_INTERACTIVE_UNCOMPRESS_CHOICES, max_length=1,
        help_text=_('Whether to expand or not compressed archives.'),
        verbose_name=_('Uncompress')
    )
    delete_after_upload = models.BooleanField(
        default=True,
        help_text=_(
            'Delete the file after is has been successfully uploaded.'
        ),
        verbose_name=_('Delete after upload')
    )
    '''



class SourceBackendWatchFolder(SourceBackend):
    can_compress = True
    field_order = ('interval', 'uncompress', 'folder_path')
    fields = {
        'interval': {
            'label': _('Interval'),
            'class': 'django.forms.IntegerField',
            'default': DEFAULT_INTERVAL,
            'help_text': _(
                'Interval in seconds between checks for new documents.'
            ), 'required': True
        },
        'uncompress': {
            'label': _('Uncompress'),
            'class': 'django.forms.ChoiceField', 'default': '',
            'help_text': _(
                'Whether to expand or not compressed archives.'
            ), 'kwargs': {
                'choices': SOURCE_INTERACTIVE_UNCOMPRESS_CHOICES,
            }, 'required': True
        },
        'folder_path': {
            'label': _('Folder path'),
            'class': 'django.forms.CharField', 'default': '',
            'help_text': _(
                'Server side filesystem path.'
            ), 'kwargs': {
                'max_length': 255,
            }, 'required': True
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

    '''
    interval = models.PositiveIntegerField(
        default=DEFAULT_INTERVAL,
        help_text=_('Interval in seconds between checks for new documents.'),
        verbose_name=_('Interval')
    )
    document_type = models.ForeignKey(
        help_text=_(
            'Assign a document type to documents uploaded from this source.'
        ), on_delete=models.CASCADE, to=DocumentType,
        related_name='interval_sources', verbose_name=_('Document type')
    )
    uncompress = models.CharField(
        choices=SOURCE_UNCOMPRESS_CHOICES,
        help_text=_('Whether to expand or not, compressed archives.'),
        max_length=1, verbose_name=_('Uncompress')
    )
    folder_path = models.CharField(
        help_text=_('Server side filesystem path to scan for files.'),
        max_length=255, verbose_name=_('Folder path')
    )
    include_subdirectories = models.BooleanField(
        help_text=_(
            'If checked, not only will the folder path be scanned for files '
            'but also its subdirectories.'
        ),
        verbose_name=_('Include subdirectories?')
    )

    objects = models.Manager()

    class Meta:
        verbose_name = _('Watch folder')
        verbose_name_plural = _('Watch folders')
    '''

class SourceBackendWebForm(SourceBackend):
    can_compress = True
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
    upload_form_class = WebFormUploadForm
    widgets = {
        'uncompress': {
            'class': 'django.forms.widgets.Select', 'kwargs': {
                'attrs': {'class': 'select2'},
            }
        }
    }

    def __init__(self, model_instance_id, **kwargs):
        self.model_instance_id = model_instance_id

    def get_upload_file_object(self, form_data):
        return SourceUploadedFile(
            source=self.model_instance_id, file=form_data['file']
        )

