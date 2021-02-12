from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('motd', '0006_auto_20210212_0934'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='announcement',
            options={'verbose_name': 'Announcement', 'verbose_name_plural': 'Announcements'},
        ),
        migrations.AlterField(
            model_name='announcement',
            name='end_datetime',
            field=models.DateTimeField(blank=True, help_text='Date and time until when this announcement is to be displayed.', null=True, verbose_name='End date time'),
        ),
        migrations.AlterField(
            model_name='announcement',
            name='label',
            field=models.CharField(help_text='Short description of this announcement.', max_length=32, verbose_name='Label'),
        ),
        migrations.AlterField(
            model_name='announcement',
            name='message',
            field=models.TextField(help_text='The actual test to be displayed.', verbose_name='Text'),
        ),
        migrations.AlterField(
            model_name='announcement',
            name='start_datetime',
            field=models.DateTimeField(blank=True, help_text='Date and time after which this announcement will be displayed.', null=True, verbose_name='Start date time'),
        ),
    ]
