from django.utils.translation import ugettext_lazy as _

from mayan.apps.events.classes import EventTypeNamespace

namespace = EventTypeNamespace(label=_('Announcements'), name='motd')

event_announcement_created = namespace.add_event_type(
    label=_('Announcement created'), name='message_created'
)
event_announcement_edited = namespace.add_event_type(
    label=_('Announcement edited'), name='message_edited'
)
