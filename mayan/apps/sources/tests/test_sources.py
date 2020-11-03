import fcntl
from multiprocessing import Process
from pathlib import Path
import shutil

import mock

from django.core import mail
from django.utils.encoding import force_bytes, force_text

from django_celery_beat.models import PeriodicTask

from mayan.apps.common.serialization import yaml_dump
from mayan.apps.documents.models import Document
from mayan.apps.documents.tests.base import GenericDocumentTestCase
from mayan.apps.documents.tests.literals import (
    TEST_COMPRESSED_DOCUMENT_PATH, TEST_NON_ASCII_DOCUMENT_FILENAME,
    TEST_NON_ASCII_DOCUMENT_PATH, TEST_NON_ASCII_COMPRESSED_DOCUMENT_PATH,
    TEST_SMALL_DOCUMENT_FILENAME, TEST_SMALL_DOCUMENT_PATH
)
from mayan.apps.metadata.models import MetadataType

from ..literals import SOURCE_UNCOMPRESS_CHOICE_Y
from ..models.email_sources import EmailBaseModel, IMAPEmail, POP3Email
from ..models.scanner_sources import SaneScanner

from .literals import (
    TEST_EMAIL_ATTACHMENT_AND_INLINE, TEST_EMAIL_BASE64_FILENAME,
    TEST_EMAIL_BASE64_FILENAME_FROM, TEST_EMAIL_BASE64_FILENAME_SUBJECT,
    TEST_EMAIL_INLINE_IMAGE, TEST_EMAIL_NO_CONTENT_TYPE,
    TEST_EMAIL_NO_CONTENT_TYPE_STRING, TEST_EMAIL_ZERO_LENGTH_ATTACHMENT,
    TEST_WATCHFOLDER_SUBFOLDER
)
from .mixins import WebFormSourceTestMixin, WatchFolderTestMixin
from .mocks import MockIMAPServer, MockPOP3Mailbox


class WebFormSourceTestCase(WebFormSourceTestMixin, GenericDocumentTestCase):
    auto_upload_test_document = False

    def test_upload_compressed_file(self):
        self.test_source.uncompress = SOURCE_UNCOMPRESS_CHOICE_Y
        self.test_source.save()

        with open(file=TEST_COMPRESSED_DOCUMENT_PATH, mode='rb') as file_object:
            self.test_source.handle_upload(
                document_type=self.test_document_type,
                file_object=file_object,
                expand=(
                    self.test_source.uncompress == SOURCE_UNCOMPRESS_CHOICE_Y
                )
            )

        self.assertEqual(Document.objects.count(), 2)
        self.assertTrue(
            'first document.pdf' in Document.objects.values_list(
                'label', flat=True
            )
        )
        self.assertTrue(
            'second document.pdf' in Document.objects.values_list(
                'label', flat=True
            )
        )
