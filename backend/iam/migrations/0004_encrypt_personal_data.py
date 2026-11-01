from django.db import migrations, models

from common import crypto
from iam.models import dni_blind_index, normalize_dni, phone_blind_index

ENCRYPTED = ("dni", "email", "phone_number")


def encrypt_users(apps, schema_editor):
    User = apps.get_model("iam", "User")
    for user in User.objects.all():
        user.dni = normalize_dni(user.dni)
        for name in ENCRYPTED:
            column = f"{name}_enc"
            setattr(user, column, crypto.encrypt(getattr(user, name), crypto.context("iam_user", column, user.pk)))
        user.dni_index = dni_blind_index(user.dni)
        user.phone_index = phone_blind_index(user.phone_prefix, user.phone_number)
        user.save()


def decrypt_users(apps, schema_editor):
    User = apps.get_model("iam", "User")
    for user in User.objects.all():
        for name in ENCRYPTED:
            column = f"{name}_enc"
            setattr(user, name, crypto.decrypt(getattr(user, column), crypto.context("iam_user", column, user.pk)))
        user.save()


class Migration(migrations.Migration):

    dependencies = [
        ('iam', '0003_hash_user_pin'),
    ]

    operations = [
        # Old columns become nullable so that the migration can be reversed.
        migrations.AlterField('user', 'dni', models.CharField(max_length=16, null=True, unique=True)),
        migrations.AlterField('user', 'email', models.CharField(max_length=255, null=True)),
        migrations.AlterField('user', 'phone_number', models.CharField(max_length=16, null=True)),
        migrations.AddField('user', 'dni_enc', models.TextField(default=''), preserve_default=False),
        migrations.AddField('user', 'dni_index', models.CharField(max_length=64, null=True)),
        migrations.AddField('user', 'email_enc', models.TextField(default=''), preserve_default=False),
        migrations.AddField('user', 'phone_number_enc', models.TextField(default=''), preserve_default=False),
        migrations.AddField(
            'user', 'phone_index', models.CharField(db_index=True, default='', max_length=64),
            preserve_default=False,
        ),
        migrations.RunPython(encrypt_users, decrypt_users),
        migrations.RemoveField('user', 'dni'),
        migrations.RemoveField('user', 'email'),
        migrations.RemoveField('user', 'phone_number'),
        migrations.AlterField('user', 'dni_index', models.CharField(max_length=64, unique=True)),
    ]
