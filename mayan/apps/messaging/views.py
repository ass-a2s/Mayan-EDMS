import logging

from django.contrib import messages
from django.template import RequestContext
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _, ungettext

from mayan.apps.views.generics import (
    MultipleObjectConfirmActionView, SingleObjectCreateView,
    SingleObjectDetailView, SingleObjectEditView, SingleObjectListView
)

from .forms import MessageDetailForm
from .icons import icon_message_list
from .links import link_message_create
from .models import Message
from .permissions import (
    permission_message_create, permission_message_delete,
    permission_message_edit, permission_message_view
)

logger = logging.getLogger(name=__name__)


class MessageCreateView(SingleObjectCreateView):
    fields = ('user', 'subject', 'body')
    model = Message
    #view_permission = permission_message_create

    def get_extra_context(self):
        return {
            'title': _('Create message'),
        }

    def get_instance_extra_data(self):
        return {
            'sender_object': self.request.user,
            '_event_actor': self.request.user
        }


class MessageDeleteView(MultipleObjectConfirmActionView):
    error_message = _('Error deleting message "%(instance)s"; %(exception)s')
    #model = Message
    #object_permission = permission_message_delete
    pk_url_kwarg = 'message_id'
    post_action_redirect = reverse_lazy(viewname='messaging:message_list')
    success_message_single = _('Message "%(object)s" deleted successfully.')
    success_message_singular = _('%(count)d message deleted successfully.')
    success_message_plural = _('%(count)d messages deleted successfully.')
    title_single = _('Delete message: %(object)s.')
    title_singular = _('Delete the %(count)d selected message.')
    title_plural = _('Delete the %(count)d selected message.')

    def get_extra_context(self):
        context = {
            'delete_view': True,
        }

        if self.object_list.count() == 1:
            context.update(
                {
                    'object': self.object_list.first()
                }
            )

        return context

    def get_source_queryset(self):
        return self.request.user.messages.all()

    def object_action(self, instance, form=None):
        instance.delete()


class MessageDetailView(SingleObjectDetailView):
    form_class = MessageDetailForm
    #object_permission = permission_document_view
    pk_url_kwarg = 'message_id'
    #source_queryset = Document.valid

    def get_extra_context(self):
        return {
            'object': self.object,
            'title': _('Details of message: %s') % self.object,
        }

    def get_source_queryset(self):
        return self.request.user.messages.all()


"""
class MessageEditView(SingleObjectEditView):
    fields = ('label', 'message', 'enabled', 'start_datetime', 'end_datetime')
    model = Message
    object_permission = permission_message_edit
    pk_url_kwarg = 'message_id'
    post_action_redirect = reverse_lazy(viewname='motd:message_list')

    def get_extra_context(self):
        return {
            'object': self.object,
            'title': _('Edit message: %s') % self.object,
        }

    def get_instance_extra_data(self):
        return {
            '_event_actor': self.request.user
        }
"""
"""
class MessageListView(SingleObjectListView):
    model = Message
    object_permission = permission_message_view

    def get_extra_context(self):
        return {
            'hide_link': True,
            'hide_object': True,
            'no_results_icon': icon_message_list,
            'no_results_main_link': link_message_create.resolve(
                context=RequestContext(request=self.request)
            ),
            'no_results_text': _(
                'Messages are displayed in the login view. You can use '
                'messages to convery information about your organzation, '
                'announcements or usage guidelines for your users.'
            ),
            'no_results_title': _('No messages available'),
            'title': _('Messages'),
        }

class NotificationMarkRead(ConfirmView):
    post_action_redirect = reverse_lazy(
        viewname='events:user_notifications_list'
    )

    def get_extra_context(self):
        return {
            'title': _('Mark the selected notification as read?')
        }

    def get_queryset(self):
        return self.request.user.notifications.all()

    def view_action(self, form=None):
        self.get_queryset().filter(
            pk=self.kwargs['notification_id']
        ).update(read=True)

        messages.success(
            message=_('Notification marked as read.'), request=self.request
        )

"""


class MessageListView(SingleObjectListView):
    def get_extra_context(self):
        return {
            'hide_object': True,
            'no_results_icon': icon_message_list,
            'no_results_main_link': link_message_create.resolve(
                context=RequestContext(request=self.request)
            ),
            'no_results_text': _(
                'Here you will find text messages from other users or from '
                'the system.'
            ),
            'no_results_title': _('There are no messages'),
            'object': self.request.user,
            'title': _('Messages'),
        }

    def get_source_queryset(self):
        return self.request.user.messages.all()
