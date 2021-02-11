from django.apps import apps
from django.utils.translation import ugettext_lazy as _

from mayan.apps.navigation.classes import Link
from mayan.apps.navigation.utils import get_cascade_condition

from .icons import icon_message_create, icon_message_delete, icon_message_list
from .permissions import (
    permission_message_create, permission_message_delete,
    permission_message_edit, permission_message_view
)


def get_unread_message_count(context):
    Message = apps.get_model(
        app_label='messaging', model_name='Message'
    )
    if context.request.user.is_authenticated:
        return Message.objects.filter(
            user=context.request.user
        ).filter(read=False).count()


link_message_create = Link(
    icon=icon_message_create, permissions=(permission_message_create,),
    text=_('Create message'), view='messaging:message_create'
)
link_message_multiple_delete = Link(
    icon=icon_message_delete, tags='dangerous', text=_('Delete'),
    view='messaging:message_multiple_delete'
)
link_message_single_delete = Link(
    args='object.pk', icon=icon_message_delete,
    #permissions=(permission_message_delete,),
    tags='dangerous', text=_('Delete'), view='messaging:message_single_delete'
)
"""
link_message_edit = Link(
    args='object.pk', icon=icon_message_edit,
    permissions=(permission_message_edit,), text=_('Edit'),
    view='motd:message_edit'
)
"""

link_message_list = Link(
    badge_text=get_unread_message_count, icon=icon_message_list,
    text='', view='messaging:message_list'
)
