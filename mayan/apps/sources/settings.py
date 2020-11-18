import os

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from mayan.apps.smart_settings.classes import SettingNamespace

from .setting_migrations import SourcesSettingMigration

namespace = SettingNamespace(
    label=_('Sources'), migration_class=SourcesSettingMigration,
    name='sources', version='0002'
)

setting_scanimage_path = namespace.add_setting(
    global_name='SOURCES_SCANIMAGE_PATH', default='/usr/bin/scanimage',
    help_text=_(
        'File path to the scanimage program used to control image scanners.'
    ),
    is_path=True
)
setting_source_cache_storage = namespace.add_setting(
    global_name='SOURCES_SOURCE_CACHE_STORAGE_BACKEND',
    default='django.core.files.storage.FileSystemStorage', help_text=_(
        'Path to the Storage subclass used to store cached '
        'source image files.'
    )
)
setting_source_cache_storage_arguments = namespace.add_setting(
    global_name='SOURCES_SOURCE_CACHE_STORAGE_BACKEND_ARGUMENTS',
    default={
        'location': os.path.join(settings.MEDIA_ROOT, 'source_cache')
    }, help_text=_(
        'Arguments to pass to the SOURCES_SOURCE_CACHE_STORAGE_BACKEND.'
    )
)
