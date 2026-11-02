from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("iam", "0005_user_role"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("customer", "Customer"),
                    ("admin", "Administrator"),
                    ("auditor", "Auditor"),
                    ("operations", "Operations"),
                ],
                default="customer",
                max_length=16,
            ),
        ),
    ]
