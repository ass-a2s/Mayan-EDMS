from django.apps import apps
from django.utils.translation import ugettext_lazy as _

from mayan.apps.converter.layers import layer_saved_transformations

#from .source_backends.literals import SOURCE_UNCOMPRESS_CHOICE_ASK


def handler_create_default_document_source(sender, **kwargs):
    #WebFormSource = apps.get_model(
    #    app_label='sources', model_name='WebFormSource'
    #)

    #if not WebFormSource.objects.count():
    #    WebFormSource.objects.create(
    #        label=_('Default'), uncompress=SOURCE_UNCOMPRESS_CHOICE_ASK
    #    )
    pass


def handler_delete_interval_source_periodic_task(sender, instance, **kwargs):
    #TODO:Fix
    #for interval_source in instance.interval_sources.all():
    #    interval_source.delete_periodic_task()
    pass


def handler_initialize_periodic_tasks(sender, **kwargs):
    POP3Email = apps.get_model(app_label='sources', model_name='POP3Email')
    IMAPEmail = apps.get_model(app_label='sources', model_name='IMAPEmail')
    WatchFolderSource = apps.get_model(
        app_label='sources', model_name='WatchFolderSource'
    )

    for source in POP3Email.objects.filter(enabled=True):
        source.save()

    for source in IMAPEmail.objects.filter(enabled=True):
        source.save()

    for source in WatchFolderSource.objects.filter(enabled=True):
        source.save()
