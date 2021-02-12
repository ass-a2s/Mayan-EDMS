from django.db import migrations


def code_copy_messages(apps, schema_editor):
    AccessControlList = apps.get_model(
        app_label='acls', model_name='AccessControlList'
    )
    Announcement = apps.get_model(
        app_label='announcements', model_name='Announcement'
    )
    ContentType = apps.get_model(
        app_label='contenttypes', model_name='ContentType'
    )
    Message = apps.get_model(app_label='motd', model_name='Message')

    for message in Message.objects.using(alias=schema_editor.connection.alias).all():
        Announcement.objects.create(
            label=message.label,
            text=message.message,
            enabled=message.enabled,
            start_datetime=message.start_datetime,
            end_datetime=message.end_datetime
        )

    raise Exception

def reverse_code_copy_messages(apps, schema_editor):
    Announcement = apps.get_model(
        app_label='announcements', model_name='Announcement'
    )
    Message = apps.get_model(app_label='motd', model_name='Message')

    for announcement in Announcement.objects.using(alias=schema_editor.connection.alias).all():
        Message.objects.create(
            label=announcement.label,
            message=announcement.text,
            enabled=announcement.enabled,
            start_datetime=announcement.start_datetime,
            end_datetime=announcement.end_datetime
        )


class Migration(migrations.Migration):
    dependencies = [
        ('announcements', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            code=code_copy_messages,
            reverse_code=reverse_code_copy_messages
        ),
    ]





