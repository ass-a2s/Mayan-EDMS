from mayan.apps.rest_api import generics

from .classes import Permission
from .models import Role
from .permissions import (
    permission_role_create, permission_role_delete, permission_role_edit,
    permission_role_view
)
from .serializers import (
    PermissionSerializer, RoleSerializer, WritableRoleSerializer
)


class APIPermissionList(generics.ListAPIView):
    """
    get: Returns a list of all the available permissions.
    """
    serializer_class = PermissionSerializer
    queryset = Permission.all()


class APIRoleListView(generics.ListCreateAPIView):
    """
    get: Returns a list of all the roles.
    post: Create a new role.
    """
    mayan_object_permissions = {'GET': (permission_role_view,)}
    mayan_view_permissions = {'POST': (permission_role_create,)}
    queryset = Role.objects.all()

    def get_instance_extra_data(self):
        return {'_event_actor': self.request.user}

    def get_serializer(self, *args, **kwargs):
        if not self.request:
            return None

        return super().get_serializer(*args, **kwargs)

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return RoleSerializer
        elif self.request.method == 'POST':
            return WritableRoleSerializer


class APIRoleView(generics.RetrieveUpdateDestroyAPIView):
    """
    delete: Delete the selected role.
    get: Return the details of the selected role.
    patch: Edit the selected role.
    put: Edit the selected role.
    """
    lookup_url_kwarg = 'role_id'
    mayan_object_permissions = {
        'GET': (permission_role_view,),
        'PUT': (permission_role_edit,),
        'PATCH': (permission_role_edit,),
        'DELETE': (permission_role_delete,)
    }
    queryset = Role.objects.all()

    def get_instance_extra_data(self):
        return {'_event_actor': self.request.user}

    def get_serializer(self, *args, **kwargs):
        if not self.request:
            return None

        return super().get_serializer(*args, **kwargs)

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return RoleSerializer
        elif self.request.method in ('PATCH', 'PUT'):
            return WritableRoleSerializer
