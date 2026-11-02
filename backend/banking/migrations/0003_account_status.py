from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("banking", "0002_card"),
    ]

    operations = [
        migrations.AddField(
            model_name="account",
            name="status",
            field=models.CharField(default="ACTIVE", max_length=8),
        ),
    ]
