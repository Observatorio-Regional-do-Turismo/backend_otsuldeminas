import django_ckeditor_5.fields
import django.utils.timezone
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("website_backend", "0013_alter_description_ckeditor5"),
    ]

    operations = [
        migrations.CreateModel(
            name="Noticia",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("slug", models.SlugField(max_length=255, unique=True)),
                ("summary", models.TextField(blank=True)),
                ("content", django_ckeditor_5.fields.CKEditor5Field(blank=True, config_name="default")),
                ("published_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("is_featured", models.BooleanField(default=False)),
                ("category", models.CharField(blank=True, max_length=100)),
                ("author", models.CharField(blank=True, max_length=255)),
                ("source_url", models.URLField(blank=True, max_length=500)),
                ("tags", models.JSONField(blank=True, default=list)),
                (
                    "cidade",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="noticias",
                        to="website_backend.cidade",
                    ),
                ),
                (
                    "igr",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="noticias",
                        to="website_backend.igr",
                    ),
                ),
            ],
            options={
                "verbose_name": "Notícia",
                "verbose_name_plural": "Notícias",
                "ordering": ["-published_at", "-id"],
            },
        ),
    ]
