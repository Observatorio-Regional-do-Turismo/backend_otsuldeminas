from pathlib import Path
import shutil

from django.conf import settings
from django.db import migrations


def normalize_image_paths(apps, schema_editor):
    Imagem = apps.get_model("website_backend", "Imagem")
    media_root = Path(settings.MEDIA_ROOT)

    for imagem in Imagem.objects.filter(image__startswith="_media/"):
        old_name = imagem.image.name
        new_name = old_name.removeprefix("_media/")
        old_path = media_root / old_name
        new_path = media_root / new_name

        if old_path.exists() and not new_path.exists():
            new_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(old_path, new_path)

        imagem.image.name = new_name
        imagem.save(update_fields=["image"])


def restore_image_paths(apps, schema_editor):
    Imagem = apps.get_model("website_backend", "Imagem")
    media_root = Path(settings.MEDIA_ROOT)

    for imagem in Imagem.objects.exclude(image__startswith="_media/"):
        old_name = imagem.image.name
        new_name = f"_media/{old_name}"
        old_path = media_root / old_name
        new_path = media_root / new_name

        if old_path.exists() and not new_path.exists():
            new_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(old_path, new_path)

        imagem.image.name = new_name
        imagem.save(update_fields=["image"])


class Migration(migrations.Migration):

    dependencies = [
        ("website_backend", "0005_alter_imagem_image"),
    ]

    operations = [
        migrations.RunPython(normalize_image_paths, restore_image_paths),
    ]
