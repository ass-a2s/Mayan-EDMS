from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.generics import get_object_or_404 as rest_get_object_or_404
from rest_framework.response import Response

from mayan.apps.acls.models import AccessControlList
from mayan.apps.documents.models.document_models import DocumentType
from mayan.apps.documents.permissions import permission_document_create
from mayan.apps.permissions.classes import Permission
from mayan.apps.rest_api import generics
from mayan.apps.storage.classes import DefinedStorage
from mayan.apps.storage.models import SharedUploadedFile

from ...literals import (
    STAGING_FILE_IMAGE_TASK_TIMEOUT, STORAGE_NAME_SOURCE_CACHE_FOLDER
)
from ...models import Source
from ...permissions import permission_sources_view
from ...tasks import (
    task_generate_staging_file_image, task_process_document_upload
)

from .serializers import (
    StagingFolderFileSerializer, StagingFolderFileUploadSerializer
)


class APIStagingSourceFileView(generics.RetrieveDestroyAPIView):
    """
    get: Details of the selected staging file.
    """
    serializer_class = StagingFolderFileSerializer

    def get_object(self):
        if self.request.method == 'DELETE':
            Permission.check_user_permissions(
                permissions=(permission_sources_view,),
                user=self.request.user
            )

        staging_folder = get_object_or_404(
            klass=Source, pk=self.kwargs['staging_folder_pk']
        ).get_backend_instance()
        return staging_folder.get_file(
            encoded_filename=self.kwargs['encoded_filename']
        )


class APIStagingSourceFileImageView(generics.RetrieveAPIView):
    """
    get: Returns an image representation of the selected staging folder file.
    """
    def get_serializer(self, *args, **kwargs):
        return None

    def get_serializer_class(self):
        return None

    def retrieve(self, request, *args, **kwargs):
        width = request.GET.get('width')
        height = request.GET.get('height')

        task = task_generate_staging_file_image.apply_async(
            kwargs=dict(
                staging_folder_pk=self.kwargs['staging_folder_pk'],
                encoded_filename=self.kwargs['encoded_filename'],
                width=width, height=height
            )
        )

        kwargs = {'timeout': STAGING_FILE_IMAGE_TASK_TIMEOUT}
        if settings.DEBUG:
            # In debug more, task are run synchronously, causing this method
            # to be called inside another task. Disable the check of nested
            # tasks when using debug mode.
            kwargs['disable_sync_subtasks'] = False

        cache_filename = task.get(**kwargs)
        storage_staging_file_image_cache = DefinedStorage.get(
            name=STORAGE_NAME_SOURCE_CACHE_FOLDER
        ).get_storage_instance()

        with storage_staging_file_image_cache.open(name=cache_filename) as file_object:
            response = HttpResponse(file_object.read(), content_type='image')
            return response


class APIStagingSourceFileUploadView(generics.GenericAPIView):
    """
    post: Upload the selected staging folder file.
    """
    serializer_class = StagingFolderFileUploadSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        queryset = AccessControlList.objects.restrict_queryset(
            queryset=DocumentType.objects.all(),
            permission=permission_document_create,
            user=self.request.user
        )

        document_type = rest_get_object_or_404(
            queryset=queryset, pk=serializer['document_type'].value
        )

        staging_folder = rest_get_object_or_404(
            queryset=Source, pk=self.kwargs['staging_folder_pk']
        )

        staging_file_object = staging_folder.get_upload_file_object(
            form_data={'staging_file_id': self.kwargs['encoded_filename']}
        )

        shared_uploaded_file = SharedUploadedFile.objects.create(
            file=staging_file_object.file
        )

        kwargs = {
            'callback_kwargs': staging_folder.get_callback_kwargs(),
            'description': staging_folder.get_document_description(),
            'document_type_id': document_type.pk,
            'label': staging_folder.get_document_label(),
            'language': staging_folder.get_document_language(),
            'shared_uploaded_file_id': shared_uploaded_file.pk,
            'source_id': staging_folder.model_instance_id,
            'user_id': self.request.user.pk,
        }
        kwargs.update(staging_folder.get_task_extra_kwargs())

        task_process_document_upload.apply_async(kwargs=kwargs)

        return Response(status=status.HTTP_202_ACCEPTED)
