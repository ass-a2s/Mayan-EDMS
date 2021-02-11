from django import forms
from django.utils.translation import ugettext_lazy as _

from mayan.apps.views.forms import DetailForm

from .models import Message


class MessageDetailForm(DetailForm):
    def __init__(self, *args, **kwargs):
        #message = kwargs['instance']

        extra_fields = [
            {
                'label': _('Date and time'),
                'field': 'date_time',
                'widget': forms.widgets.DateTimeInput
            },
            {'label': _('Sender'), 'field': 'sender_object'},
            {'field': 'subject'},
            {'field': 'body'},

        ]

        kwargs['extra_fields'] = extra_fields
        super().__init__(*args, **kwargs)

    class Meta:
        fields = ()
        model = Message
