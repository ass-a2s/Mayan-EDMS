from rest_framework import serializers

from .models import Source


class SourceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        extra_kwargs = {
            'url': {'view_name': 'rest_api:source-detail'},
        }
        fields = (
            'backend_data', 'backend_path', 'enabled', 'id', 'label', 'url'
        )
        model = Source
