from django.test import override_settings

from mayan.apps.documents.models import Document
from mayan.apps.documents.permissions import (
    permission_document_create, permission_document_file_new
)
from mayan.apps.documents.tests.base import GenericDocumentViewTestCase
from mayan.apps.documents.tests.literals import (
    TEST_COMPRESSED_DOCUMENT_PATH, TEST_DOCUMENT_DESCRIPTION,
    TEST_SMALL_DOCUMENT_CHECKSUM, TEST_SMALL_DOCUMENT_PATH
)
from mayan.apps.metadata.models import MetadataType
from mayan.apps.testing.tests.base import GenericViewTestCase

from ..models import Source
from ..permissions import (
    permission_sources_create, permission_sources_delete,
    permission_sources_edit, permission_sources_view
)
from ..source_backends.literals import SOURCE_UNCOMPRESS_CHOICE_ALWAYS

from .literals import TEST_SOURCE_LABEL
from .mixins import (
    DocumentFileUploadViewTestMixin, DocumentUploadIssueViewTestMixin,
    DocumentUploadWizardViewTestMixin, EmailSourceBackendViewTestMixin,
    StagingFolderTestMixin, StagingFolderViewTestMixin,
    WebFormSourceTestMixin, SourceViewTestMixin, WatchFolderTestMixin
)
from .source_backends import SourceBackendTestEmail  # Import to enable backend




'''
class DocumentUploadWizardViewTestCase(
    WebFormSourceTestMixin, DocumentUploadWizardViewTestMixin,
    GenericDocumentViewTestCase
):
    auto_upload_test_document = False

    def test_upload_compressed_file(self):
        self.test_source.uncompress = SOURCE_UNCOMPRESS_CHOICE_ALWAYS
        self.test_source.save()

        self.grant_access(
            obj=self.test_document_type, permission=permission_document_create
        )

        response = self._request_upload_wizard_view(
            document_path=TEST_COMPRESSED_DOCUMENT_PATH
        )
        self.assertEqual(response.status_code, 302)

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

    def test_upload_wizard_without_permission(self):
        response = self._request_upload_wizard_view()
        self.assertEqual(response.status_code, 403)

        self.assertEqual(Document.objects.count(), 0)

    def test_upload_wizard_with_permission(self):
        self.grant_permission(permission=permission_document_create)

        response = self._request_upload_wizard_view()
        self.assertEqual(response.status_code, 302)

        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(
            Document.objects.first().file_latest.checksum,
            TEST_SMALL_DOCUMENT_CHECKSUM
        )

    def test_upload_wizard_with_document_type_access(self):
        """
        Test uploading of documents by granting the document create
        permission for the document type to the user
        """
        # Create an access control entry giving the role the document
        # create permission for the selected document type.
        self.grant_access(
            obj=self.test_document_type, permission=permission_document_create
        )

        with open(file=TEST_SMALL_DOCUMENT_PATH, mode='rb') as file_object:
            response = self.post(
                viewname='sources:document_upload_interactive', kwargs={
                    'source_id': self.test_source.pk
                }, data={
                    'source-file': file_object,
                    'document_type_id': self.test_document_type.pk,
                }
            )
        self.assertEqual(response.status_code, 302)

        self.assertEqual(Document.objects.count(), 1)

    def test_upload_interactive_view_no_permission(self):
        response = self._request_upload_interactive_view()
        self.assertEqual(response.status_code, 403)

    def test_upload_interactive_view_with_access(self):
        self.grant_access(
            permission=permission_document_create, obj=self.test_document_type
        )
        response = self._request_upload_interactive_view()
        self.assertContains(
            response=response, text=self.test_source.label, status_code=200
        )

    @override_settings(DOCUMENTS_LANGUAGE='fra')
    def test_default_document_language_setting(self):
        self.grant_access(
            permission=permission_document_create, obj=self.test_document_type
        )
        response = self._request_upload_interactive_view()
        self.assertContains(
            response=response,
            text='<option value="fra" selected>French</option>',
            status_code=200
        )


class DocumentUploadIssueTestCase(
    DocumentUploadIssueViewTestMixin, GenericDocumentViewTestCase
):
    auto_upload_test_document = False
    auto_login_superuser = True
    auto_login_user = False
    create_test_case_superuser = True
    create_test_case_user = False

    def test_issue_25(self):
        # Create new webform source
        self._request_test_source_create_view()
        self.assertEqual(WebFormSource.objects.count(), 1)

        # Upload the test document
        with open(file=TEST_SMALL_DOCUMENT_PATH, mode='rb') as file_object:
            self.post(
                viewname='sources:document_upload_interactive', data={
                    'document-language': 'eng',
                    'source-file': file_object,
                    'document_type_id': self.test_document_type.pk
                }
            )
        self.assertEqual(Document.objects.count(), 1)

        self.test_document = Document.objects.first()
        # Test for issue 25 during creation
        # ** description fields was removed from upload from **
        self.assertEqual(self.test_document.description, '')

        # Reset description
        self.test_document.description = TEST_DOCUMENT_DESCRIPTION
        self.test_document.save()
        self.assertEqual(self.test_document.description, TEST_DOCUMENT_DESCRIPTION)

        # Test for issue 25 during editing
        self._request_test_source_edit_view()
        # Fetch document again and test description
        self.test_document = Document.objects.first()
        self.assertEqual(self.test_document.description, TEST_DOCUMENT_DESCRIPTION)


class DocumentFileUploadViewTestCase(
    DocumentFileUploadViewTestMixin, WebFormSourceTestMixin,
    GenericDocumentViewTestCase
):
    def test_document_file_upload_view_no_permission(self):
        file_count = self.test_document.files.count()

        response = self._request_document_file_upload_view()

        self.assertEqual(response.status_code, 403)
        self.test_document.refresh_from_db()
        self.assertEqual(
            self.test_document.files.count(), file_count
        )

    def test_document_file_upload_view_with_access(self):
        self.grant_access(
            obj=self.test_document,
            permission=permission_document_file_new
        )
        file_count = self.test_document.files.count()

        response = self._request_document_file_upload_view()
        self.assertEqual(response.status_code, 302)

        self.test_document.refresh_from_db()
        self.assertEqual(
            self.test_document.files.count(), file_count + 1
        )

    def test_document_file_upload_no_source_view_no_permission(self):
        file_count = self.test_document.files.count()

        response = self._request_document_file_upload_no_source_view()
        self.assertEqual(response.status_code, 403)

        self.test_document.refresh_from_db()
        self.assertEqual(
            self.test_document.files.count(), file_count
        )

    def test_document_file_upload_no_source_view_with_access(self):
        self.grant_access(
            obj=self.test_document,
            permission=permission_document_file_new
        )
        file_count = self.test_document.files.count()

        response = self._request_document_file_upload_no_source_view()

        self.assertEqual(response.status_code, 302)
        self.test_document.refresh_from_db()
        self.assertEqual(
            self.test_document.files.count(), file_count + 1
        )

    def test_document_file_upload_view_preserve_filename_with_access(self):
        self.grant_access(
            obj=self.test_document,
            permission=permission_document_file_new
        )
        file_count = self.test_document.files.count()

        response = self._request_document_file_upload_view()
        self.assertEqual(response.status_code, 302)

        self.test_document.refresh_from_db()
        self.assertEqual(
            self.test_document.files.count(), file_count + 1
        )
        self.assertEqual(
            self.test_document.file_latest.filename,
            self.test_document_filename
        )
'''



class EmailSourceViewTestCase(
    EmailSourceBackendViewTestMixin, GenericDocumentViewTestCase
):
    auto_upload_test_document = False

    def test_email_source_create_view(self):
        self.grant_permission(permission=permission_sources_create)

        source_count = Source.objects.count()

        response = self._request_test_email_source_create_view()

        self.assertEqual(response.status_code, 302)

        self.assertEqual(Source.objects.count(), source_count + 1)

    def test_metadata_type_validation_invalid_from(self):
        test_metadata_type = MetadataType.objects.create(
            name='test_metadata_type'
        )

        self.grant_permission(permission=permission_sources_create)

        source_count = Source.objects.count()

        response = self._request_test_email_source_create_view(
            extra_data={
                'from_metadata_type_id': test_metadata_type.pk,
            }
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Source.objects.count(), source_count)

    def test_metadata_type_validation_valid_from(self):
        test_metadata_type = MetadataType.objects.create(
            name='test_metadata_type'
        )

        self.test_document_type.metadata.create(metadata_type=test_metadata_type)

        self.grant_permission(permission=permission_sources_create)

        source_count = Source.objects.count()

        response = self._request_test_email_source_create_view(
            extra_data={
                'from_metadata_type_id': test_metadata_type.pk,
            }
        )
        self.assertEqual(response.status_code, 302)

        self.assertEqual(Source.objects.count(), source_count + 1)

    def test_metadata_type_validation_invalid_subject(self):
        test_metadata_type = MetadataType.objects.create(
            name='test_metadata_type'
        )

        self.grant_permission(permission=permission_sources_create)

        source_count = Source.objects.count()

        response = self._request_test_email_source_create_view(
            extra_data={
                'subject_metadata_type_id': test_metadata_type.pk
            }
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Source.objects.count(), source_count)

    def test_metadata_type_validation_valid_subject(self):
        test_metadata_type = MetadataType.objects.create(
            name='test_metadata_type'
        )

        self.test_document_type.metadata.create(metadata_type=test_metadata_type)

        self.grant_permission(permission=permission_sources_create)

        source_count = Source.objects.count()

        response = self._request_test_email_source_create_view(
            extra_data={
                'subject_metadata_type_id': test_metadata_type.pk
            }
        )
        self.assertEqual(response.status_code, 302)

        self.assertEqual(Source.objects.count(), source_count + 1)


class SourceViewTestCase(
    WebFormSourceTestMixin, SourceViewTestMixin, GenericViewTestCase
):
    def test_source_create_view_no_permission(self):
        source_count = Source.objects.count()

        response = self._request_test_source_create_view()
        self.assertEqual(response.status_code, 403)

        self.assertEqual(Source.objects.count(), source_count)

    def test_source_create_view_with_permission(self):
        self.grant_permission(permission=permission_sources_create)

        source_count = Source.objects.count()

        response = self._request_test_source_create_view()
        self.assertEqual(response.status_code, 302)

        self.assertEqual(self.test_source.label, TEST_SOURCE_LABEL)
        self.assertEqual(Source.objects.count(), source_count + 1)

    def test_source_delete_view_no_permission(self):
        self._create_test_web_form_source()

        source_count = Source.objects.count()

        response = self._request_test_source_delete_view()
        self.assertEqual(response.status_code, 404)

        self.assertEqual(Source.objects.count(), source_count)

    def test_source_delete_view_with_access(self):
        self._create_test_web_form_source()

        self.grant_access(
            obj=self.test_source, permission=permission_sources_delete
        )

        source_count = Source.objects.count()

        response = self._request_test_source_delete_view()
        self.assertEqual(response.status_code, 302)

        self.assertEqual(Source.objects.count(), source_count - 1)

    def test_source_edit_view_no_permission(self):
        self._create_test_web_form_source()
        test_instance_values = self._model_instance_to_dictionary(
            instance=self.test_source
        )

        response = self._request_test_source_edit_view()
        self.assertEqual(response.status_code, 404)

        self.test_source.refresh_from_db()
        self.assertEqual(
            self._model_instance_to_dictionary(
                instance=self.test_source
            ), test_instance_values
        )

    def test_source_edit_view_with_access(self):
        self._create_test_web_form_source()
        test_instance_values = self._model_instance_to_dictionary(
            instance=self.test_source
        )
        self.grant_access(
            obj=self.test_source, permission=permission_sources_edit
        )

        response = self._request_test_source_edit_view()
        self.assertEqual(response.status_code, 302)

        self.test_source.refresh_from_db()
        self.assertNotEqual(
            self._model_instance_to_dictionary(
                instance=self.test_source
            ), test_instance_values
        )

    def test_source_list_view_no_permission(self):
        self._create_test_web_form_source()

        response = self._request_test_source_list_view()
        self.assertEqual(response.status_code, 200)

    def test_source_list_view_with_access(self):
        self._create_test_web_form_source()

        self.grant_access(
            obj=self.test_source, permission=permission_sources_view
        )

        response = self._request_test_source_list_view()
        self.assertContains(
            response=response, text=self.test_source.label, status_code=200
        )

    def test_source_test_get_view_no_permission(self):
        self._create_test_web_form_source()

        response = self._request_test_source_test_get_view()
        self.assertEqual(response.status_code, 404)

    def test_source_test_get_view_with_access(self):
        self._create_test_web_form_source()

        self.grant_access(
            obj=self.test_source, permission=permission_sources_edit
        )

        response = self._request_test_source_test_get_view()
        self.assertEqual(response.status_code, 200)


'''
class StagingFolderViewTestCase(
    StagingFolderTestMixin, StagingFolderViewTestMixin, GenericViewTestCase
):
    def setUp(self):
        super().setUp()
        self._create_test_staging_folder()
        self._copy_test_document()

    def test_staging_file_delete_no_permission(self):
        staging_file_count = len(list(self.test_staging_folder.get_files()))
        staging_file = list(self.test_staging_folder.get_files())[0]

        response = self._request_test_staging_file_delete_view(
            staging_folder=self.test_staging_folder, staging_file=staging_file
        )
        self.assertEqual(response.status_code, 404)

        self.assertEqual(
            staging_file_count,
            len(list(self.test_staging_folder.get_files()))
        )

    def test_staging_file_delete_with_permission(self):
        self.grant_permission(permission=permission_sources_view)

        staging_file_count = len(list(self.test_staging_folder.get_files()))
        staging_file = list(self.test_staging_folder.get_files())[0]

        response = self._request_test_staging_file_delete_view(
            staging_folder=self.test_staging_folder, staging_file=staging_file
        )
        self.assertEqual(response.status_code, 302)

        self.assertNotEqual(
            staging_file_count,
            len(list(self.test_staging_folder.get_files()))
        )
'''
