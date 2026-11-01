from django.contrib.auth.hashers import make_password
from django.db import migrations, models

from common import crypto


def hash_existing_pins(apps, schema_editor):
    User = apps.get_model("iam", "User")
    for user in User.objects.all():
        plain = crypto.decrypt_legacy(user.pin_iv, user.pin_ciphertext, user.pin_tag)
        user.pin = make_password(plain)
        user.save(update_fields=["pin"])


class Migration(migrations.Migration):

    dependencies = [
        ('iam', '0002_delete_session'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='pin',
            field=models.CharField(default='', max_length=128),
            preserve_default=False,
        ),
        migrations.RunPython(hash_existing_pins, migrations.RunPython.noop),
        migrations.RemoveField(model_name='user', name='pin_iv'),
        migrations.RemoveField(model_name='user', name='pin_ciphertext'),
        migrations.RemoveField(model_name='user', name='pin_tag'),
    ]
