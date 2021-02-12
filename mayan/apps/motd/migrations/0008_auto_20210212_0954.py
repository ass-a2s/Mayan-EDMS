from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('motd', '0007_auto_20210212_0941'),
    ]

    operations = [
        migrations.RenameField(
            model_name='announcement',
            old_name='message',
            new_name='text',
        ),
    ]
