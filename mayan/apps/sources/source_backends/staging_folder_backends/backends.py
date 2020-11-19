import base64
import logging
import os
import time
from urllib.parse import quote_plus, unquote_plus

from furl import furl

from django.core.files import File
from django.core.files.base import ContentFile
from django.conf.urls import url
from django.urls import reverse
from django.utils.encoding import force_text
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from mayan.apps.appearance.classes import Icon
from mayan.apps.common.menus import menu_object
from mayan.apps.converter.classes import ConverterBase
from mayan.apps.converter.transformations import TransformationResize
from mayan.apps.navigation.classes import Link, SourceColumn
from mayan.apps.storage.classes import DefinedStorage
from mayan.apps.storage.models import SharedUploadedFile

from ...classes import SourceBackend
from ...forms import StagingUploadForm
from ...literals import STORAGE_NAME_SOURCE_CACHE_FOLDER
from ...permissions import permission_sources_view

from ..mixins import (
    SourceBackendCompressedMixin, SourceBackendInteractiveMixin,
    SourceBaseMixin
)

from .api_views import (
    APIStagingSourceFileView, APIStagingSourceFileImageView,
    APIStagingSourceFileUploadView
)
from .views import StagingFileDeleteView
from .widgets import StagingFileThumbnailWidget

__all__ = ('SourceBackendStagingFolder',)
logger = logging.getLogger(name=__name__)


class StagingFile:
    """
    Simple class to extend the File class to add preview capabilities
    files in a directory on a storage
    """
    def __init__(self, staging_folder, filename=None, encoded_filename=None):
        self.staging_folder = staging_folder
        if encoded_filename:
            self.encoded_filename = str(encoded_filename)
            self.filename = base64.urlsafe_b64decode(
                unquote_plus(self.encoded_filename)
            ).decode('utf8')
        else:
            self.filename = filename
            self.encoded_filename = quote_plus(base64.urlsafe_b64encode(
                filename.encode('utf8')
            ))

    def __str__(self):
        return force_text(s=self.filename)

    def as_file(self):
        return File(
            file=open(
                file=self.get_full_path(), mode='rb'
            ), name=self.filename
        )

    @property
    def cache_filename(self):
        return '{}{}'.format(
            self.staging_folder.model_instance_id, self.encoded_filename
        )

    def delete(self):
        self.storage.delete(self.cache_filename)
        os.unlink(self.get_full_path())

    def generate_image(self, *args, **kwargs):
        transformation_list = self.get_combined_transformation_list(*args, **kwargs)

        # Check is transformed image is available
        logger.debug('transformations cache filename: %s', self.cache_filename)

        if self.storage.exists(self.cache_filename):
            logger.debug(
                'staging file cache file "%s" found', self.cache_filename
            )
        else:
            logger.debug(
                'staging file cache file "%s" not found', self.cache_filename
            )
            image = self.get_image(transformations=transformation_list)
            with self.storage.open(name=self.cache_filename, mode='wb+') as file_object:
                file_object.write(image.getvalue())

        return self.cache_filename

    def get_api_image_url(self, *args, **kwargs):
        final_url = furl()
        final_url.args = kwargs
        final_url.path = reverse(
            'rest_api:stagingfolderfile-image', kwargs={
                'staging_folder_pk': self.staging_folder.model_instance_id,
                'encoded_filename': self.encoded_filename
            }
        )

        return final_url.tostr()

    def get_combined_transformation_list(self, *args, **kwargs):
        """
        Return a list of transformation containing the server side
        staging file transformation as well as tranformations created
        from the arguments as transient interactive transformation.
        """
        # Convert arguments into transformations
        transformations = kwargs.get('transformations', [])

        # Set sensible defaults if the argument is not specified or if the
        # argument is None
        width = self.staging_folder.kwargs.get('preview_width')
        height = self.staging_folder.kwargs.get('preview_height')

        # Generate transformation hash
        transformation_list = []

        # Interactive transformations second
        for transformation in transformations:
            transformation_list.append(transformation)

        if width:
            transformation_list.append(
                TransformationResize(width=width, height=height)
            )

        return transformation_list

    def get_date_time_created(self):
        return time.ctime(os.path.getctime(self.get_full_path()))

    def get_full_path(self):
        return os.path.join(
            self.staging_folder.kwargs['folder_path'], self.filename
        )

    def get_image(self, transformations=None):
        cache_filename = self.cache_filename
        file_object = None

        try:
            file_object = open(file=self.get_full_path(), mode='rb')
            converter = ConverterBase.get_converter_class()(
                file_object=file_object
            )

            page_image = converter.get_page()

            # Since open "wb+" doesn't create files, check if the file
            # exists, if not then create it
            if not self.storage.exists(cache_filename):
                self.storage.save(name=cache_filename, content=ContentFile(content=''))

            with self.storage.open(name=cache_filename, mode='wb+') as file_object:
                file_object.write(page_image.getvalue())
        except Exception as exception:
            # Cleanup in case of error
            logger.error(
                'Error creating staging file cache "%s"; %s',
                cache_filename, exception
            )
            self.storage.delete(cache_filename)
            if file_object:
                file_object.close()
            raise

        for transformation in transformations:
            converter.transform(transformation=transformation)

        result = converter.get_page()
        file_object.close()
        return result

    @cached_property
    def storage(self):
        return DefinedStorage.get(
            name=STORAGE_NAME_SOURCE_CACHE_FOLDER
        ).get_storage_instance()


class SourceBackendStagingFolder(
    SourceBackendCompressedMixin, SourceBackendInteractiveMixin,
    SourceBaseMixin, SourceBackend
):
    field_order = (
        'folder_path', 'preview_width', 'preview_height',
        'delete_after_upload'
    )
    fields = {
        'folder_path': {
            'class': 'django.forms.CharField',
            'default': '',
            'help_text': _(
                'Server side filesystem path.'
            ),
            'kwargs': {
                'max_length': 255,
            },
            'label': _('Folder path'),
            'required': True
        },
        'preview_width': {
            'class': 'django.forms.IntegerField',
            'help_text': _(
                'Width value to be passed to the converter backend.'
            ),
            'kwargs': {
                'min_value': 0
            },
            'label': _('Preview width'),
            'required': True
        },
        'preview_height': {
            'class': 'django.forms.IntegerField',
            'help_text': _(
                'Height value to be passed to the converter backend.'
            ),
            'kwargs': {
                'min_value': 0
            },
            'label': _('Preview height'),
            'required': False
        },
        'delete_after_upload': {
            'class': 'django.forms.BooleanField',
            'help_text': _(
                'Delete the file after is has been successfully uploaded.'
            ),
            'label': _('Delete after upload'),
            'required': False
        }
    }
    icon_staging_folder_file = Icon(driver_name='fontawesome', symbol='file')
    label = _('Staging folder')
    upload_form_class = StagingUploadForm

    @classmethod
    def intialize(cls):
        from ...urls import urlpatterns

        from mayan.apps.rest_api.urls import api_version_urls

        icon_staging_file_delete = Icon(driver_name='fontawesome', symbol='times')

        link_staging_file_delete = Link(
            args=('source.pk', 'object.encoded_filename',), keep_query=True,
            icon_class=icon_staging_file_delete,
            permissions=(permission_sources_view,),
            tags='dangerous', text=_('Delete'), view='sources:staging_file_delete',
        )
        menu_object.bind_links(
            links=(link_staging_file_delete,), sources=(StagingFile,)
        )
        html_widget = StagingFileThumbnailWidget()

        SourceColumn(
            func=lambda context: context['object'].get_date_time_created(),
            label=_('Created'), source=StagingFile,
        )

        SourceColumn(
            source=StagingFile,
            label=_('Thumbnail'),
            func=lambda context: html_widget.render(
                instance=context['object'],
            )
        )

        urlpatterns += (
            url(
                regex=r'^staging_folders/(?P<staging_folder_id>\d+)/files/(?P<encoded_filename>.+)/delete/$',
                name='staging_file_delete', view=StagingFileDeleteView.as_view()
            ),
        )

        api_version_urls.extend(
            [
                url(
                    regex=r'^staging_folders_files/(?P<staging_folder_pk>[0-9]+)/(?P<encoded_filename>.+)/image/$',
                    name='stagingfolderfile-image',
                    view=APIStagingSourceFileImageView.as_view()
                ),
                url(
                    regex=r'^staging_folders_files/(?P<staging_folder_pk>[0-9]+)/(?P<encoded_filename>.+)/upload/$',
                    name='stagingfolderfile-upload',
                    view=APIStagingSourceFileUploadView.as_view()
                ),
                url(
                    regex=r'^staging_folders_files/(?P<staging_folder_pk>[0-9]+)/(?P<encoded_filename>.+)/$',
                    name='stagingfolderfile-detail',
                    view=APIStagingSourceFileView.as_view()
                )
            ]
        )

    #TODO: Implement post upload action
    def clean_up_upload_file(self, upload_file_object):
        if self.kwargs['delete_after_upload']:
            try:
                upload_file_object.extra_data.delete()
            except Exception as exception:
                logger.error(
                    'Error deleting staging file: %s; %s',
                    upload_file_object, exception
                )
                raise Exception(
                    _('Error deleting staging file; %s') % exception
                )

    def get_file(self, *args, **kwargs):
        return StagingFile(staging_folder=self, *args, **kwargs)

    def get_files(self):
        try:
            for entry in sorted([os.path.normcase(f) for f in os.listdir(self.kwargs['folder_path']) if os.path.isfile(os.path.join(self.kwargs['folder_path'], f))]):
                yield self.get_file(filename=entry)
        except OSError as exception:
            logger.error(
                'Unable get list of staging files from source: %s; %s',
                self, exception
            )
            raise Exception(
                _('Unable get list of staging files: %s') % exception
            )

    def get_shared_uploaded_files(self):
        staging_file = self.get_file(
            encoded_filename=self.process_kwargs['forms']['source_form'].cleaned_data['staging_file_id']
        )
        return (
            SharedUploadedFile.objects.create(file=staging_file.as_file()),
        )

    def get_view_context(self, context, request):
        subtemplates_list = [
            {
                'name': 'appearance/generic_multiform_subtemplate.html',
                'context': {
                    'forms': context['forms'],
                },
            },
            {
                'name': 'appearance/generic_list_subtemplate.html',
                'context': {
                    'hide_link': True,
                    'no_results_icon': SourceBackendStagingFolder.icon_staging_folder_file,
                    'no_results_text': _(
                        'This could mean that the staging folder is '
                        'empty. It could also mean that the '
                        'operating system user account being used '
                        'for Mayan EDMS doesn\'t have the necessary '
                        'file system permissions for the folder.'
                    ),
                    'no_results_title': _(
                        'No staging files available'
                    ),
                    'object_list': list(self.get_files()),
                }
            },
        ]

        return {'subtemplates_list': subtemplates_list}
