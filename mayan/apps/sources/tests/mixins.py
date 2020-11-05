import json
import shutil

from django.db.models import Q

from mayan.apps.documents.literals import DOCUMENT_FILE_ACTION_PAGES_NEW
from mayan.apps.documents.tests.literals import (
    TEST_DOCUMENT_DESCRIPTION, TEST_SMALL_DOCUMENT_PATH
)
from mayan.apps.storage.utils import fs_cleanup, mkdtemp

from ..literals import (
    SOURCE_UNCOMPRESS_CHOICE_NEVER, SOURCE_UNCOMPRESS_CHOICE_ALWAYS
)
from ..models import Source
#from ..models.staging_folder_sources import StagingFolderSource
#from ..models.watch_folder_sources import WatchFolderSource
#from ..models.webform_sources import WebFormSource

from .literals import (
    TEST_SOURCE_LABEL, TEST_SOURCE_LABEL_EDITED, TEST_STAGING_PREVIEW_WIDTH
)

SOURCE_BACKEND_STAGING_FOLDER_PATH = 'mayan.apps.sources.sources.SourceBackendStagingFolder'
SOURCE_BACKEND_WATCHFOLDER_PATH = 'mayan.apps.sources.sources.SourceBackendWatchFolder'
SOURCE_BACKEND_WEB_FORM_PATH = 'mayan.apps.sources.sources.SourceBackendWebForm'


class DocumentUploadIssueTestMixin:
    def _request_test_source_create_view(self):
        return self.post(
            viewname='sources:source_create', kwargs={
                'source_type_name': SOURCE_CHOICE_WEB_FORM
            }, data={
                'enabled': True, 'label': 'test', 'uncompress': 'n'
            }
        )

    def _request_test_source_edit_view(self):
        return self.post(
            viewname='documents:document_properties_edit', kwargs={
                'document_id': self.test_document.pk
            },
            data={
                'description': TEST_DOCUMENT_DESCRIPTION,
                'label': self.test_document.label,
                'language': self.test_document.language
            }
        )


class DocumentUploadWizardViewTestMixin:
    def _request_upload_wizard_view(self, document_path=TEST_SMALL_DOCUMENT_PATH):
        with open(file=document_path, mode='rb') as file_object:
            return self.post(
                viewname='sources:document_upload_interactive', kwargs={
                    'source_id': self.test_source.pk
                }, data={
                    'source-file': file_object,
                    'document_type_id': self.test_document_type.pk,
                }
            )

    def _request_upload_interactive_view(self):
        return self.get(
            viewname='sources:document_upload_interactive', data={
                'document_type_id': self.test_document_type.pk,
            }
        )


class DocumentFileUploadViewTestMixin:
    def _request_document_file_upload_view(self):
        with open(file=TEST_SMALL_DOCUMENT_PATH, mode='rb') as file_object:
            return self.post(
                viewname='sources:document_file_upload', kwargs={
                    'document_id': self.test_document.pk,
                    'source_id': self.test_source.pk,
                }, data={
                    'document-action': DOCUMENT_FILE_ACTION_PAGES_NEW,
                    'source-file': file_object
                }
            )

    def _request_document_file_upload_no_source_view(self):
        with open(file=TEST_SMALL_DOCUMENT_PATH, mode='rb') as file_object:
            return self.post(
                viewname='sources:document_file_upload', kwargs={
                    'document_id': self.test_document.pk,
                }, data={
                    'document-action': DOCUMENT_FILE_ACTION_PAGES_NEW,
                    'source-file': file_object
                }
            )


class StagingFolderAPIViewTestMixin:
    def setUp(self):
        super().setUp()
        self.test_staging_folders = []

    def tearDown(self):
        for test_staging_folder in self.test_staging_folders:
            fs_cleanup(filename=test_staging_folder.folder_path)
            self.test_staging_folders.remove(test_staging_folder)

        super().tearDown()

    def _request_test_staging_folder_create_api_view(self):
        return self.post(
            viewname='rest_api:stagingfolder-list', data={
                'label': TEST_SOURCE_LABEL,
                'folder_path': mkdtemp(),
                'preview_width': TEST_STAGING_PREVIEW_WIDTH,
                'uncompress': SOURCE_UNCOMPRESS_CHOICE_NEVER,
            }
        )

        self.test_staging_folder = StagingFolderSource.objects.first()
        self.test_staging_folders.append(self.test_staging_folder)

    def _request_test_staging_folder_delete_api_view(self):
        return self.delete(
            viewname='rest_api:stagingfolder-detail', kwargs={
                'pk': self.test_staging_folder.pk
            }
        )

    def _request_test_staging_folder_edit_api_view(self, extra_data=None, verb='patch'):
        data = {
            'label': TEST_SOURCE_LABEL_EDITED,
        }

        if extra_data:
            data.update(extra_data)

        return getattr(self, verb)(
            viewname='rest_api:stagingfolder-detail', kwargs={
                'pk': self.test_staging_folder.pk
            }, data=data
        )

    def _request_test_staging_folder_list_api_view(self):
        return self.get(viewname='rest_api:stagingfolder-list')


class StagingFolderFileAPIViewTestMixin:
    def _request_test_staging_folder_file_delete_api_view(self):
        return self.delete(
            viewname='rest_api:stagingfolderfile-detail', kwargs={
                'staging_folder_pk': self.test_staging_folder.pk,
                'encoded_filename': self.test_staging_folder_file.encoded_filename
            }
        )

    def _request_test_staging_folder_file_detail_api_view(self):
        return self.get(
            viewname='rest_api:stagingfolderfile-detail', kwargs={
                'staging_folder_pk': self.test_staging_folder.pk,
                'encoded_filename': self.test_staging_folder_file.encoded_filename
            }
        )

    def _request_test_staging_folder_file_upload_api_view(self):
        return self.post(
            viewname='rest_api:stagingfolderfile-upload', kwargs={
                'staging_folder_pk': self.test_staging_folder.pk,
                'encoded_filename': self.test_staging_folder_file.encoded_filename
            }, data={'document_type': self.test_document_type.pk}
        )


class SourceTestMixin:
    def _create_test_source(self, backend_path, backend_data=None):
        self.test_source = Source.objects.create(
            backend_path=backend_path,
            backend_data=json.dumps(obj=backend_data),
            label=TEST_SOURCE_LABEL
        )


class StagingFolderTestMixin(SourceTestMixin):
    def setUp(self):
        super().setUp()
        self.test_staging_folders = []

    def tearDown(self):
        for test_staging_folder in self.test_staging_folders:
            #fs_cleanup(filename=test_staging_folder.folder_path)
            shutil.rmtree(
                path=test_staging_folder.get_backend_data()['folder_path']
            )
            self.test_staging_folders.remove(test_staging_folder)

        super().tearDown()

    def _copy_test_document_to_test_staging_folder(self):
        shutil.copy(
            src=TEST_SMALL_DOCUMENT_PATH,
            dst=self.test_source.get_backend_data()['folder_path']
        )
        self.test_staging_folder_file = list(
            self.test_source.get_backend_instance().get_files()
        )[0]

    def _create_test_staging_folder(self, extra_data=None):
        backend_data = {
            'folder_path': mkdtemp(),
            'preview_width': TEST_STAGING_PREVIEW_WIDTH,
            'uncompress': SOURCE_UNCOMPRESS_CHOICE_NEVER
        }

        if extra_data:
            backend_data.update(extra_data)

        self._create_test_source(
            backend_path=SOURCE_BACKEND_STAGING_FOLDER_PATH,
            backend_data=backend_data
        )
        self.test_staging_folders.append(self.test_source)


class StagingFolderViewTestMixin:
    def _request_test_staging_file_delete_view(self, staging_folder, staging_file):
        return self.post(
            viewname='sources:staging_file_delete', kwargs={
                'staging_folder_id': staging_folder.pk,
                'encoded_filename': staging_file.encoded_filename
            }
        )


class SourceViewTestMixin:
    def _request_test_source_backend_selection_view(self):
        return self.get(
            viewname='sources:source_backend_selection'
        )

    def _request_test_source_check_get_view(self):
        return self.get(
            viewname='sources:source_check', kwargs={
                'source_id': self.test_source.pk
            }
        )

    def _request_test_source_check_post_view(self):
        return self.post(
            viewname='sources:source_check', kwargs={
                'source_id': self.test_source.pk
            }
        )

    def _request_test_source_create_view(self):
        pk_list = list(Source.objects.values_list('pk', flat=True))

        response = self.post(
            kwargs={
                'backend_path': TEST_SOURCE_BACKEND_PATH
            }, viewname='sources:source_create', data={
                'enabled': True, 'label': TEST_SOURCE_LABEL,
                'uncompress': SOURCE_UNCOMPRESS_CHOICE_NEVER
            }
        )

        try:
            self.test_source = Source.objects.get(~Q(pk__in=pk_list))
        except Source.DoesNotExist:
            self.test_source = None

        return response

    def _request_test_source_delete_view(self):
        return self.post(
            viewname='sources:source_delete', kwargs={
                'source_id': self.test_source.pk
            }
        )

    def _request_test_source_edit_view(self):
        return self.post(
            viewname='sources:source_edit', kwargs={
                'source_id': self.test_source.pk
            }, data={
                'label': TEST_SOURCE_LABEL_EDITED,
                'uncompress': self.test_source.get_backend_data().get(
                    'uncompress'
                )
            }
        )

    def _request_test_source_list_view(self):
        return self.get(viewname='sources:source_list')


class WatchFolderTestMixin(SourceTestMixin):
    def setUp(self):
        super().setUp()
        self.temporary_directory = mkdtemp()

    def tearDown(self):
        shutil.rmtree(path=self.temporary_directory)
        super().tearDown()

    def _create_test_watchfolder(self, extra_data=None):
        backend_data = {
            'document_type_id': self.test_document_type.pk,
            'folder_path': self.temporary_directory,
            'include_subdirectories': False,
            'uncompress': SOURCE_UNCOMPRESS_CHOICE_NEVER
        }

        if extra_data:
            backend_data.update(extra_data)

        self._create_test_source(
            backend_path=SOURCE_BACKEND_WATCHFOLDER_PATH,
            backend_data=backend_data
        )


class WebFormSourceTestMixin(SourceTestMixin):
    def _create_test_web_form_source(self, extra_data=None):
        backend_data = {'uncompress': SOURCE_UNCOMPRESS_CHOICE_NEVER}

        if extra_data:
            backend_data.update(extra_data)

        self._create_test_source(
            backend_path=SOURCE_BACKEND_WEB_FORM_PATH,
            backend_data=backend_data
        )
