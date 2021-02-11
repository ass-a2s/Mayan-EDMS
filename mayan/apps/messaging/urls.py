from django.conf.urls import url

#from .api_views import APIMessageListView, APIMessageView
from .views import MessageCreateView, MessageDeleteView, MessageDetailView, MessageListView


urlpatterns = [
    url(
        regex=r'^messages/$', name='message_list',
        view=MessageListView.as_view()
    ),
    url(
        regex=r'^messages/create/$', name='message_create',
        view=MessageCreateView.as_view()
    ),
    url(
        regex=r'^messages/(?P<message_id>\d+)/delete/$',
        name='message_single_delete', view=MessageDeleteView.as_view()
    ),
    url(
        regex=r'^messages/(?P<message_id>\d+)/details/$',
        name='message_detail', view=MessageDetailView.as_view()
    ),
    url(
        regex=r'^messages/multiple/delete/$',
        name='message_multiple_delete', view=MessageDeleteView.as_view()
    ),
    #url(
    #    regex=r'^messages/(?P<message_id>\d+)/edit/$', name='message_edit',
    #    view=MessageEditView.as_view()
    #),
]

#api_urls = [
#    url(
#        regex=r'^messages/$', name='message-list',
#        view=APIMessageListView.as_view()
#    ),
#    url(
#        regex=r'^messages/(?P<message_id>[0-9]+)/$', name='message-detail',
#        view=APIMessageView.as_view()
#    ),
#]
