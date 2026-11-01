from django.db import migrations, models


def admins_to_role(apps, schema_editor):
    User = apps.get_model("iam", "User")
    User.objects.filter(is_admin=True).update(role="admin")


def role_to_admins(apps, schema_editor):
    User = apps.get_model("iam", "User")
    User.objects.filter(role="admin").update(is_admin=True)


class Migration(migrations.Migration):

    dependencies = [
        ("iam", "0003_hash_user_pin"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[("customer", "Customer"), ("admin", "Administrator"), ("auditor", "Auditor")],
                default="customer",
                max_length=16,
            ),
        ),
        migrations.RunPython(admins_to_role, role_to_admins),
        migrations.RemoveField(model_name="user", name="is_admin"),
    ]
