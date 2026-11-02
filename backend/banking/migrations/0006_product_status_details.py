from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("banking", "0005_account_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="account",
            name="status_reason",
            field=models.CharField(default="", max_length=255),
        ),
        migrations.AddField(
            model_name="account",
            name="status_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="card",
            name="status_reason",
            field=models.CharField(default="", max_length=255),
        ),
        migrations.AddField(
            model_name="card",
            name="status_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
