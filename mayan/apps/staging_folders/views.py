from django.utils.translation import ugettext_lazy as _

from mayan.apps.sources.models import Source
from mayan.apps.sources.permissions import permission_sources_view
from mayan.apps.views.generics import SingleObjectDeleteView
from mayan.apps.views.mixins import ExternalObjectViewMixin

__all__ = ('StagingFileDeleteView',)


class StagingFileDeleteView(ExternalObjectViewMixin, SingleObjectDeleteView):
    external_object_class = Source
    external_object_permission = permission_sources_view
    external_object_pk_url_kwarg = 'staging_folder_id'

    def get_extra_context(self):
        return {
            'object': self.object,
            'object_name': _('Staging file'),
            'title': _('Delete staging file "%s"?') % self.object,
        }

    def get_object(self):
        return self.external_object.get_backend_instance().get_file(
            encoded_filename=self.kwargs['encoded_filename']
        )
