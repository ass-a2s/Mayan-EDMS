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
#from ..exceptions import SourceException
from ..literals import SOURCE_INTERVAL_UNCOMPRESS_CHOICES
from ..tasks import task_process_document_upload

from .mixins import (
    SourceBackendCompressedMixin, SourceBackendEmailMixin,
    SourceBackendPeriodicMixin, SourceBaseMixin
)

__all__ = ('SourceBackendIMAPEmail',)
logger = logging.getLogger(name=__name__)


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

class SourceBackendIMAPEmail(
    SourceBackendCompressedMixin, SourceBackendEmailMixin,
    SourceBackendPeriodicMixin, SourceBaseMixin, SourceBackend
):
    #can_uncompress = True
    #field_order = ('interval', 'uncompress',)
    #fields = {
    #    'interval': {
    #        'class': 'django.forms.IntegerField',
    #        'default': DEFAULT_INTERVAL,
    #        'help_text': _(
    #            'Interval in seconds between checks for new documents.'
    #        ),
    #        'label': _('Interval'),
    #        'required': True
    #    },
    #    'uncompress': {
    #        'class': 'django.forms.ChoiceField', 'default': '',
    #        'help_text': _(
    #            'Whether to expand or not compressed archives.'
    #        ),
    #        'kwargs': {
    #            'choices': SOURCE_INTERACTIVE_UNCOMPRESS_CHOICES,
    #        },
    #        'label': _('Uncompress'),
    #        'required': True
    #    },
    #}
    label = _('IMAP email')
    #widgets = {
    #    'uncompress': {
    #        'class': 'django.forms.widgets.Select', 'kwargs': {
    #            'attrs': {'class': 'select2'},
    #        }
    #    }
    #}
    uncompress_choices = SOURCE_INTERVAL_UNCOMPRESS_CHOICES

    '''


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

"""

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
"""
