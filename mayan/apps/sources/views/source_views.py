import logging

from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.template import RequestContext
from django.urls import reverse, reverse_lazy
from django.utils.translation import ugettext_lazy as _

from mayan.apps.views.generics import (
    ConfirmView, FormView, SingleObjectCreateView, SingleObjectDeleteView,
    SingleObjectDynamicFormCreateView, SingleObjectDynamicFormEditView,
    SingleObjectEditView, SingleObjectListView
)
from mayan.apps.views.mixins import ExternalObjectMixin

from ..classes import SourceBackend
from ..forms import SourceBackendSelectionForm, SourceBackendDynamicForm
from ..icons import icon_setup_sources
from ..links import (
    link_setup_source_create_imap_email, link_setup_source_create_pop3_email,
    link_setup_source_create_staging_folder,
    link_setup_source_create_watch_folder, link_setup_source_create_webform,
    link_setup_source_create_sane_scanner
)
from ..models import Source
from ..permissions import (
    permission_sources_setup_create, permission_sources_setup_delete,
    permission_sources_setup_edit, permission_sources_setup_view,
    permission_staging_file_delete
)
from ..tasks import task_check_interval_source
from ..utils import get_class, get_form_class

__all__ = (
    'SourceCheckView', 'SourceCreateView', 'SourceDeleteView',
    'SourceEditView', 'SourceListView', 'StagingFileDeleteView'
)
logger = logging.getLogger(name=__name__)


class SourceCheckView(ExternalObjectMixin, ConfirmView):
    """
    Trigger the task_check_interval_source task for a given source to
    test/debug their configuration irrespective of the schedule task setup.
    """
    external_object_permission = permission_sources_setup_create
    external_object_pk_url_kwarg = 'source_id'
    external_object_class = Source

    def get_extra_context(self):
        return {
            'object': self.external_object,
            'subtitle': _(
                'This will execute the source check code even if the source '
                'is not enabled. Sources that delete content after '
                'downloading will not do so while being tested. Check the '
                'source\'s error log for information during testing. A '
                'successful test will clear the error log.'
            ), 'title': _(
                'Trigger check for source "%s"?'
            ) % self.external_object,
        }

    def view_action(self):
        task_check_interval_source.apply_async(
            kwargs={
                'source_id': self.external_object.pk, 'test': True
            }
        )

        messages.success(
            message=_('Source check queued.'), request=self.request
        )


"""
class SourceCreateView(SingleObjectCreateView):
    post_action_redirect = reverse_lazy(
        viewname='sources:setup_source_list'
    )
    view_permission = permission_sources_setup_create

    def get_extra_context(self):
        return {
            'object': self.kwargs['source_type_name'],
            'title': _(
                'Create new source of type: %s'
            ) % get_class(
                source_type_name=self.kwargs['source_type_name']
            ).class_fullname(),
        }

    def get_form_class(self):
        return get_form_class(
            source_type_name=self.kwargs['source_type_name']
        )
"""

class SourceDeleteView(SingleObjectDeleteView):
    model = Source
    object_permission = permission_sources_setup_delete
    pk_url_kwarg = 'source_id'
    post_action_redirect = reverse_lazy(
        viewname='sources:setup_source_list'
    )

    def get_extra_context(self):
        return {
            'object': self.object,
            'title': _('Delete the source: %s?') % self.object,
        }

    #def get_form_class(self):
    #    return get_form_class(source_type_name=self.get_object().source_type)

    #def get_object(self):
    #    return self.external_object


class SourceEditView(SingleObjectDynamicFormEditView):
    form_class = SourceBackendDynamicForm
    model = Source
    object_permission = permission_sources_setup_edit
    pk_url_kwarg = 'source_id'

    def get_extra_context(self):
        return {
            'title': _('Edit source: %s') % self.object,
        }

    def get_form_schema(self):
        backend = self.object.get_backend()
        result = {
            'fields': backend.fields,
            'widgets': getattr(backend, 'widgets', {})
        }
        if hasattr(backend, 'field_order'):
            result['field_order'] = backend.field_order

        return result

'''
class SourceEditView(ExternalObjectMixin, SingleObjectEditView):
    external_object_permission = permission_sources_setup_edit
    external_object_pk_url_kwarg = 'source_id'
    external_object_queryset = Source.objects.select_subclasses()
    post_action_redirect = reverse_lazy(
        viewname='sources:setup_source_list'
    )
    view_permission = permission_sources_setup_edit

    def get_extra_context(self):
        return {
            'object': self.get_object(),
            'title': _('Edit source: %s') % self.get_object(),
        }

    def get_form_class(self):
        return get_form_class(source_type_name=self.get_object().source_type)

    def get_object(self):
        return self.external_object
'''

class SourceListView(SingleObjectListView):
    model = Source
    object_permission = permission_sources_setup_view
    #source_queryset = Source.objects.select_subclasses()

    def get_extra_context(self):
        return {
            'hide_link': True,
            'hide_object': True,
            'no_results_icon': icon_setup_sources,
            'no_results_secondary_links': [
                link_setup_source_create_webform.resolve(
                    context=RequestContext(request=self.request)
                ),
                link_setup_source_create_imap_email.resolve(
                    context=RequestContext(request=self.request)
                ),
                link_setup_source_create_pop3_email.resolve(
                    context=RequestContext(request=self.request)
                ),
                link_setup_source_create_sane_scanner.resolve(
                    context=RequestContext(request=self.request)
                ),
                link_setup_source_create_staging_folder.resolve(
                    context=RequestContext(request=self.request)
                ),
                link_setup_source_create_watch_folder.resolve(
                    context=RequestContext(request=self.request)
                ),
            ],
            'no_results_text': _(
                'Sources provide the means to upload documents. '
                'Some sources like the webform, are interactive and require '
                'user input to operate. Others like the email sources, are '
                'automatic and run on the background without user intervention.'
            ),
            'no_results_title': _('No sources available'),
            'title': _('Sources'),
        }


class SourceBackendSelectionView(FormView):
    extra_context = {
        'title': _('New source backend selection'),
    }
    form_class = SourceBackendSelectionForm
    view_permission = permission_sources_setup_create

    def form_valid(self, form):
        backend = form.cleaned_data['backend']
        return HttpResponseRedirect(
            redirect_to=reverse(
                viewname='sources:source_create', kwargs={
                    'backend_path': backend
                }
            )
        )


class SourceCreateView(SingleObjectDynamicFormCreateView):
    form_class = SourceBackendDynamicForm
    post_action_redirect = reverse_lazy(viewname='sources:setup_source_list')
    view_permission = permission_sources_setup_create

    def get_backend(self):
        try:
            return SourceBackend.get(name=self.kwargs['backend_path'])
        except KeyError:
            raise Http404(
                '{} class not found'.format(self.kwargs['backend_path'])
            )

    def get_extra_context(self):
        return {
            'title': _(
                'Create a "%s" source'
            ) % self.get_backend().label,
        }

    def get_form_schema(self):
        backend = self.get_backend()
        result = {
            'fields': backend.fields,
            'widgets': getattr(backend, 'widgets', {})
        }
        if hasattr(backend, 'field_order'):
            result['field_order'] = backend.field_order

        return result

    def get_instance_extra_data(self):
        return {'backend_path': self.kwargs['backend_path']}


class StagingFileDeleteView(ExternalObjectMixin, SingleObjectDeleteView):
    object_class = Source
    object_permission = permission_staging_file_delete
    pk_url_kwarg = 'staging_folder_id'

    def get_extra_context(self):
        return {
            'object': self.object,
            'object_name': _('Staging file'),
            'title': _('Delete staging file "%s"?') % self.object,
        }

    def get_object(self):
        return self.external_object.get_file(
            encoded_filename=self.kwargs['encoded_filename']
        )
