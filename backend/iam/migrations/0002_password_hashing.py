from django.db import migrations, models


def rehash_passwords(apps, schema_editor):
    from common import crypto
    from django.contrib.auth.hashers import make_password

    User = apps.get_model("iam", "User")
    for user in User.objects.all():
        plain = crypto.decrypt(user.password_iv, user.password_ciphertext, user.password_tag)
        user.password = make_password(plain)
        user.save(update_fields=["password"])


class Migration(migrations.Migration):

    dependencies = [
        ("iam", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="password",
            field=models.CharField(max_length=128, default=""),
            preserve_default=False,
        ),
        migrations.RunPython(rehash_passwords, migrations.RunPython.noop),
        migrations.RemoveField(model_name="user", name="password_iv"),
        migrations.RemoveField(model_name="user", name="password_ciphertext"),
        migrations.RemoveField(model_name="user", name="password_tag"),
    ]
