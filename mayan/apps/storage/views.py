from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from mayan.apps.views.generics import (
    MultipleObjectDeleteView, SingleObjectDownloadView, SingleObjectListView
)

from .icons import icon_download_file_list
from .models import DownloadFile
from .permissions import permission_download_file_view



class DownloadFileDeleteView(MultipleObjectDeleteView):
    model = DownloadFile
    #object_permission = permission_download_file_delete
    pk_url_kwarg = 'download_file_id'
    post_action_redirect = 'storage:download_file_list'

    #def get_instance_extra_data(self):
    #    return {
    #        '_event_actor': self.request.user,
    #    }


class DownloadFileDownloadViewView(SingleObjectDownloadView):
    model = DownloadFile
    pk_url_kwarg = 'download_file_id'

    def get_download_file_object(self):
        return self.object.open(mode='rb')

    def get_download_filename(self):
        return '{}.pdf'.format(force_text(self.object))


class DownloadFileListView(SingleObjectListView):
    model = DownloadFile
    object_permission = permission_download_file_view

    def get_extra_context(self):
        return {
            'hide_link': True,
            'hide_object': True,
            'no_results_icon': icon_download_file_list,
            #'no_results_main_link': link_setup_metadata_type_create.resolve(
            #    context=RequestContext(request=self.request)
            #),
            'no_results_text': _(
                'Download files are created as a results of a an external '
                'process like an export. Download files are retained over '
                'a span of time and then removed automatically.'
            ),
            'no_results_title': _('There are no files to download.'),
            'title': _('Downloads'),
        }


