from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("website_backend", "0006_normalize_imagem_paths"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="cidade",
            name="leitos",
        ),
        migrations.AddField(
            model_name="cidade",
            name="pib",
            field=models.PositiveIntegerField(default=0),
        ),
    ]