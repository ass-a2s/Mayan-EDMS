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
    TEST_SMALL_DOCUMENT_CHECKSUM, TEST_SMALL_DOCUMENT_FILENAME,
    TEST_SMALL_DOCUMENT_PATH
)
from mayan.apps.metadata.models import MetadataType

from ..literals import SOURCE_UNCOMPRESS_CHOICE_ALWAYS
from ..models import Source

from .literals import (
    TEST_EMAIL_ATTACHMENT_AND_INLINE, TEST_EMAIL_BASE64_FILENAME,
    TEST_EMAIL_BASE64_FILENAME_FROM, TEST_EMAIL_BASE64_FILENAME_SUBJECT,
    TEST_EMAIL_INLINE_IMAGE, TEST_EMAIL_NO_CONTENT_TYPE,
    TEST_EMAIL_NO_CONTENT_TYPE_STRING, TEST_EMAIL_ZERO_LENGTH_ATTACHMENT,
    TEST_WATCHFOLDER_SUBFOLDER
)
from .mixins import WebFormSourceTestMixin, WatchFolderTestMixin
from .mocks import MockIMAPServer, MockPOP3Mailbox



class SourceWatchFolderTestCase(WatchFolderTestMixin, GenericDocumentTestCase):
    auto_upload_test_document = False

    def test_upload_simple_file(self):
        self._create_test_watchfolder()

        document_count = Document.objects.count()

        shutil.copy(src=TEST_SMALL_DOCUMENT_PATH, dst=self.temporary_directory)

        self.test_source.get_backend_instance().check()

        self.assertEqual(Document.objects.count(), document_count + 1)
        self.assertEqual(
            Document.objects.first().file_latest.checksum,
            TEST_SMALL_DOCUMENT_CHECKSUM
        )

    def test_subfolder_disabled(self):
        self._create_test_watchfolder()

        test_path = Path(self.temporary_directory)
        test_subfolder = test_path.joinpath(TEST_WATCHFOLDER_SUBFOLDER)
        test_subfolder.mkdir()

        shutil.copy(
            src=TEST_SMALL_DOCUMENT_PATH, dst=test_subfolder
        )

        document_count = Document.objects.count()

        self.test_source.get_backend_instance().check()

        self.assertEqual(Document.objects.count(), document_count)

    def test_subfolder_enabled(self):
        self._create_test_watchfolder(
            extra_data={'include_subdirectories': True}
        )

        test_path = Path(self.temporary_directory)
        test_subfolder = test_path.joinpath(TEST_WATCHFOLDER_SUBFOLDER)
        test_subfolder.mkdir()

        shutil.copy(src=TEST_SMALL_DOCUMENT_PATH, dst=test_subfolder)

        document_count = Document.objects.count()

        self.test_source.get_backend_instance().check()

        self.assertEqual(Document.objects.count(), document_count + 1)

        document = Document.objects.first()

        self.assertEqual(
            document.file_latest.checksum, TEST_SMALL_DOCUMENT_CHECKSUM
        )

    def test_non_ascii_file_in_non_ascii_compressed_file(self):
        """
        Test Non-ASCII named documents inside Non-ASCII named compressed
        file. GitHub issue #163.
        """
        self._create_test_watchfolder(
            extra_data={'uncompress': SOURCE_UNCOMPRESS_CHOICE_ALWAYS}
        )

        shutil.copy(
            src=TEST_NON_ASCII_COMPRESSED_DOCUMENT_PATH,
            dst=self.temporary_directory
        )

        document_count = Document.objects.count()

        self.test_source.get_backend_instance().check()

        self.assertEqual(Document.objects.count(), document_count + 1)

        document = Document.objects.first()

        self.assertEqual(document.label, TEST_NON_ASCII_DOCUMENT_FILENAME)
        self.assertEqual(document.file_latest.exists(), True)
        self.assertEqual(document.file_latest.size, 17436)
        self.assertEqual(document.file_latest.mimetype, 'image/png')
        self.assertEqual(document.file_latest.encoding, 'binary')
        self.assertEqual(document.file_latest.page_count, 1)

    def test_locking_support(self):
        self._create_test_watchfolder()

        shutil.copy(
            src=TEST_SMALL_DOCUMENT_PATH, dst=self.temporary_directory
        )

        path_test_file = Path(
            self.temporary_directory, TEST_SMALL_DOCUMENT_FILENAME
        )

        document_count = Document.objects.count()

        with path_test_file.open(mode='rb+') as file_object:
            fcntl.lockf(file_object, fcntl.LOCK_EX | fcntl.LOCK_NB)
            process = Process(target=self.test_source.check)
            process.start()
            process.join()

        self.assertEqual(Document.objects.count(), document_count)


class SourceWebFormTestCase(WebFormSourceTestMixin, GenericDocumentTestCase):
    auto_upload_test_document = False

    def test_upload_simple_file(self):
        self._create_test_web_form_source()

        document_count = Document.objects.count()

        with open(file=TEST_SMALL_DOCUMENT_PATH, mode='rb') as file_object:
            self.test_source.handle_upload(
                document_type=self.test_document_type,
                file_object=file_object,
            )

        self.assertEqual(Document.objects.count(), document_count + 1)
        self.assertEqual(
            Document.objects.first().file_latest.checksum,
            TEST_SMALL_DOCUMENT_CHECKSUM
        )

    def test_upload_compressed_file(self):
        self._create_test_web_form_source(
            extra_data={'uncompress': SOURCE_UNCOMPRESS_CHOICE_ALWAYS}
        )

        document_count = Document.objects.count()

        with open(file=TEST_COMPRESSED_DOCUMENT_PATH, mode='rb') as file_object:
            self.test_source.handle_upload(
                document_type=self.test_document_type,
                file_object=file_object,
                expand=True
            )

        self.assertEqual(Document.objects.count(), document_count + 2)

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
