from django.utils.translation import ugettext_lazy as _

from mayan.apps.permissions import PermissionNamespace

namespace = PermissionNamespace(label=_('Storage'), name='storage')

permission_download_file_download = namespace.add_permission(
    label=_('Fetch download files'), name='download_file_download'
)
permission_download_file_view = namespace.add_permission(
    label=_('View download files'), name='download_file_view'
)
