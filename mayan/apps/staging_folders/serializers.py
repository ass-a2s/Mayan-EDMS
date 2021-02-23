import logging

from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.reverse import reverse

from mayan.apps.documents.models.document_models import DocumentType

logger = logging.getLogger(name=__name__)


class StagingFolderFileUploadSerializer(serializers.Serializer):
    document_type = serializers.PrimaryKeyRelatedField(
        label=_('Document type'), many=False,
        queryset=DocumentType.objects.all(), read_only=False
    )
    expand = serializers.BooleanField(
        default=False, label=_('Expand compressed files'), help_text=_(
            'Upload a compressed file\'s contained files as individual '
            'documents.'
        )
    )


class StagingFolderFileSerializer(serializers.Serializer):
    filename = serializers.CharField(max_length=255)
    image_url = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    encoded_filename = serializers.CharField(max_length=255)
    upload_url = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        return reverse(
            viewname='rest_api:stagingfolderfile-image',
            kwargs={
                'staging_folder_pk': obj.staging_folder.pk,
                'encoded_filename': obj.encoded_filename
            }, request=self.context.get('request')
        )

    def get_upload_url(self, obj):
        return reverse(
            viewname='rest_api:stagingfolderfile-upload',
            kwargs={
                'staging_folder_pk': obj.staging_folder.pk,
                'encoded_filename': obj.encoded_filename,
            }, request=self.context.get('request')
        )

    def get_url(self, obj):
        return reverse(
            viewname='rest_api:stagingfolderfile-detail',
            kwargs={
                'staging_folder_pk': obj.staging_folder.pk,
                'encoded_filename': obj.encoded_filename
            }, request=self.context.get('request')
        )
