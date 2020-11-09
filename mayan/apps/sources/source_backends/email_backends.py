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

from ..classes import SourceBackend
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
