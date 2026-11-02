from django.db import migrations, models
import django.utils.timezone


def migrate_admin_flag(apps, schema_editor):
    """Derive the new role column from the old is_admin flag."""
    User = apps.get_model("iam", "User")
    User.objects.filter(is_admin=True).update(role="ADMIN")


class Migration(migrations.Migration):

    dependencies = [
        ("iam", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[("USER", "User"), ("ADMIN", "Administrator"), ("AUDITOR", "Auditor")],
                db_index=True,
                default="USER",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="failed_login_attempts",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="user",
            name="locked_until",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(migrate_admin_flag, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="user",
            name="is_admin",
        ),
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.CharField(max_length=32, primary_key=True, serialize=False)),
                ("actor_id", models.CharField(db_index=True, max_length=32)),
                ("actor_dni", models.CharField(max_length=16)),
                ("action", models.CharField(db_index=True, max_length=64)),
                ("target_type", models.CharField(max_length=32)),
                ("target_id", models.CharField(default="", blank=True, max_length=64)),
                ("detail", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="SystemSetting",
            fields=[
                ("key", models.CharField(max_length=64, primary_key=True, serialize=False)),
                ("value", models.JSONField()),
                ("description", models.CharField(default="", blank=True, max_length=255)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
