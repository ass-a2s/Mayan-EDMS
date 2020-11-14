import imaplib
import logging
import poplib

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.utils.encoding import force_bytes, force_text
from django.utils.translation import ugettext_lazy as _

from mayan.apps.common.serialization import yaml_load
from mayan.apps.documents.models import Document
from mayan.apps.metadata.api import set_bulk_metadata
from mayan.apps.metadata.models import MetadataType

from ..exceptions import SourceException
from ..literals import (
    DEFAULT_IMAP_MAILBOX, DEFAULT_IMAP_SEARCH_CRITERIA,
    DEFAULT_IMAP_STORE_COMMANDS, DEFAULT_METADATA_ATTACHMENT_NAME,
    DEFAULT_POP3_TIMEOUT,
    #SOURCE_CHOICE_EMAIL_IMAP, SOURCE_CHOICE_EMAIL_POP3,
    SOURCE_UNCOMPRESS_CHOICE_NEVER, SOURCE_UNCOMPRESS_CHOICE_ALWAYS,
)

from .base import IntervalBaseModel

__all__ = ('IMAPEmail', 'POP3Email')
logger = logging.getLogger(name=__name__)


class EmailBaseModel(IntervalBaseModel):
    """
    POP3 email and IMAP email sources are non-interactive sources that
    periodically fetch emails from an email account using either the POP3 or
    IMAP email protocol. These sources are useful when users need to scan
    documents outside their office, they can photograph a paper document with
    their phones and send the image to a designated email that is setup as a
    Mayan POP3 or IMAP source. Mayan will periodically download the emails
    and process them as Mayan documents.
    """
    """
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
    """
    #objects = models.Manager()

    class Meta:
        verbose_name = _('Email source')
        verbose_name_plural = _('Email sources')


class POP3Email(EmailBaseModel):
    #source_type = SOURCE_CHOICE_EMAIL_POP3

    timeout = models.PositiveIntegerField(
        default=DEFAULT_POP3_TIMEOUT, verbose_name=_('Timeout')
    )

    objects = models.Manager()

    class Meta:
        verbose_name = _('POP email')
        verbose_name_plural = _('POP email')

    def _check_source(self, test=False):
        logger.debug(msg='Starting POP3 email fetch')
        logger.debug('host: %s', self.host)
        logger.debug('ssl: %s', self.ssl)

        if self.ssl:
            server = poplib.POP3_SSL(host=self.host, port=self.port)
        else:
            server = poplib.POP3(
                host=self.host, port=self.port, timeout=self.timeout
            )

        server.getwelcome()
        server.user(self.username)
        server.pass_(self.password)

        messages_info = server.list()

        logger.debug(msg='messages_info:')
        logger.debug(msg=messages_info)
        logger.debug('messages count: %s', len(messages_info[1]))

        for message_info in messages_info[1]:
            message_number, message_size = message_info.split()
            message_number = int(message_number)

            logger.debug('message_number: %s', message_number)
            logger.debug('message_size: %s', message_size)

            message_lines = server.retr(which=message_number)[1]
            message_complete = force_text(s=b'\n'.join(message_lines))

            EmailBaseModel.process_message(
                source=self, message_text=message_complete
            )
            if not test:
                server.dele(which=message_number)

        server.quit()
