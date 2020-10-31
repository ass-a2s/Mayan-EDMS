import logging

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from mayan.apps.navigation.classes import Link
from mayan.apps.views.generics import MultiFormView

from ..icons import icon_upload_view_link
from ..links import factory_conditional_active_by_source
from ..menus import menu_sources
from ..models import Source

__all__ = ('UploadBaseView',)
logger = logging.getLogger(name=__name__)


class UploadBaseView(MultiFormView):
    prefixes = {'source_form': 'source', 'document_form': 'document'}
    template_name = 'appearance/generic_form.html'

    @staticmethod
    def get_active_tab_links(document=None):
        return [
            UploadBaseView.get_tab_link_for_source(
                source=source, document=document
            )
            for source in Source.objects.interactive().filter(enabled=True)
        ]

    @staticmethod
    def get_tab_link_for_source(source, document=None):
        if document:
            view = 'sources:document_file_upload'
            args = ('"{}"'.format(document.pk), '"{}"'.format(source.pk),)
        else:
            view = 'sources:document_upload_interactive'
            args = ('"{}"'.format(source.pk),)

        return Link(
            args=args,
            conditional_active=factory_conditional_active_by_source(
                source=source
            ), icon_class=icon_upload_view_link, keep_query=True,
            remove_from_query=['page'], text=source.label, view=view
        )

    def dispatch(self, request, *args, **kwargs):
        interactive_sources = Source.objects.interactive().filter(enabled=True)

        if not interactive_sources.exists():
            messages.error(
                message=_(
                    'No interactive document sources have been defined or '
                    'none have been enabled, create one before proceeding.'
                ), request=request
            )
            return HttpResponseRedirect(
                redirect_to=reverse(viewname='sources:source_list')
            )

        if 'source_id' in kwargs:
            self.source = get_object_or_404(
                klass=interactive_sources,
                pk=kwargs['source_id']
            )
        else:
            self.source = interactive_sources.first()

        try:
            return super().dispatch(request, *args, **kwargs)
        except Exception as exception:
            if settings.DEBUG:
                raise
            elif request.is_ajax():
                return JsonResponse(
                    data={'error': force_text(s=exception)}, status=500
                )
            else:
                raise

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['source'] = self.source

        context.update(
            self.source.get_backend_instance().get_view_context(
                context=context, request=self.request
            )
        )

        menu_sources.bound_links['sources:document_upload_interactive'] = self.tab_links
        menu_sources.bound_links['sources:document_file_upload'] = self.tab_links

        return context
