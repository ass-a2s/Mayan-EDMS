from django.utils.translation import ugettext_lazy as _

from mayan.apps.storage.classes import DefinedStorage

from .literals import STORAGE_NAME_SOURCE_CACHE_FOLDER
from .settings import (
    setting_source_cache_storage,
    setting_source_cache_storage_arguments,
)

storage_source_cache = DefinedStorage(
    dotted_path=setting_source_cache_storage.value,
    error_message=_(
        'Unable to initialize the staging folder file image '
        'storage. Check the settings {} and {} for formatting '
        'errors.'.format(
            setting_source_cache_storage.global_name,
            setting_source_cache_storage_arguments.global_name
        )
    ),
    label=_('Staging folder files'),
    name=STORAGE_NAME_SOURCE_CACHE_FOLDER,
    kwargs=setting_source_cache_storage_arguments.value
)
