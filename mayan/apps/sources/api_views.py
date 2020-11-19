from mayan.apps.rest_api import generics

from .models import Source
from .permissions import (
    permission_sources_create, permission_sources_delete,
    permission_sources_edit, permission_sources_view
)
from .serializers import SourceSerializer


class APISourceListView(generics.ListCreateAPIView):
    """
    get: Returns a list of all the source.
    post: Create a new source.
    """
    mayan_view_permissions = {
        'GET': (permission_sources_view,),
        'POST': (permission_sources_create,)
    }
    queryset = Source.objects.all()
    serializer_class = SourceSerializer


class APISourceView(generics.RetrieveUpdateDestroyAPIView):
    """
    delete: Delete the selected source.
    get: Details of the selected source.
    patch: Edit the selected source.
    put: Edit the selected source.
    """
    mayan_object_permissions = {
        'DELETE': (permission_sources_delete,),
        'GET': (permission_sources_view,),
        'PATCH': (permission_sources_edit,),
        'PUT': (permission_sources_edit,)
    }
    queryset = Source.objects.all()
    serializer_class = SourceSerializer
