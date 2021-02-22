from drf_yasg.views import get_schema_view

from rest_framework import permissions, renderers
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.schemas.generators import EndpointEnumerator

import mayan
from mayan.apps.common.settings import setting_url_base_path

from .classes import Endpoint
from .generics import RetrieveAPIView, ListAPIView
from .serializers import AppInformationSerializer, EndpointSerializer
from .schemas import openapi_info


class AppInformationAPIView(RetrieveAPIView):
    serializer_class = AppInformationSerializer

    def get_object(self):
        return mayan


class APIRoot(ListAPIView):
    swagger_schema = None
    serializer_class = EndpointSerializer

    def get_queryset(self):
        """
        get: Return a list of all API root endpoints. This includes the
        API version root and root services.
        """
        endpoint_app_information = Endpoint(
            label='App information', viewname='rest_api:app_information'
        )
        endpoint_redoc = Endpoint(
            label='ReDoc UI', viewname='rest_api:schema-redoc'
        )
        endpoint_swagger = Endpoint(
            label='Swagger UI', viewname='rest_api:schema-swagger-ui'
        )
        endpoint_swagger_schema_json = Endpoint(
            label='API schema (JSON)', viewname='rest_api:schema-json',
            kwargs={'format': '.json'}
        )
        endpoint_swagger_schema_yaml = Endpoint(
            label='API schema (YAML)', viewname='rest_api:schema-json',
            kwargs={'format': '.yaml'}
        )
        endpoint_version = Endpoint(
            label='API version root', viewname='rest_api:api_version_root'
        )
        return [
            endpoint_version,
            endpoint_app_information,
            endpoint_swagger,
            endpoint_redoc,
            endpoint_swagger_schema_json,
            endpoint_swagger_schema_yaml
        ]


class APIVersionRoot(ListAPIView):
    swagger_schema = None
    serializer_class = EndpointSerializer

    def get_queryset(self):
        """
        get: Return a list of the API version resources and endpoint.
        """
        endpoint_enumerator = EndpointEnumerator()

        if setting_url_base_path.value:
            url_index = 4
        else:
            url_index = 3

        # Extract the resource names from the API endpoint URLs
        parsed_urls = set()
        for entry in endpoint_enumerator.get_api_endpoints():
            try:
                url = entry[0].split('/')[url_index]
            except IndexError:
                """An unknown or invalid URL"""
            else:
                parsed_urls.add(url)

        endpoints = []
        for url in sorted(parsed_urls):
            if url:
                endpoints.append(
                    Endpoint(label=url)
                )

        return endpoints


class BrowseableObtainAuthToken(ObtainAuthToken):
    """
    Obtain an API authentication token.
    """
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)


schema_view = get_schema_view(
    openapi_info,
    validators=['flex', 'ssv'],
    public=True,
    permission_classes=(permissions.AllowAny,),
)
