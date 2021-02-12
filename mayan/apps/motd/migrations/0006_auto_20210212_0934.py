from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('motd', '0005_auto_20160510_0025'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Message',
            new_name='Announcement',
        ),
    ]
