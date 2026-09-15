"""
Place this file at: <your_app>/management/commands/create_gestor_cidade.py
(create the `management/` and `management/commands/` folders with __init__.py
files if they don't exist yet)

Usage:
    python manage.py create_gestor_cidade joana joana@example.com --cidade-slug pocos-de-caldas

This will:
  1. Create (or reuse) the "Gestor de Cidade" Group with exactly the model
     permissions a city manager needs (nothing on Estado, User, Group, or
     GestorCidade itself).
  2. Create the User (is_staff=True, is_superuser=False) if it doesn't
     already exist, prompting for a password.
  3. Link the user to the given Cidade via GestorCidade.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management import CommandError
from django.core.management.base import BaseCommand

from website_backend.models import Cidade, Contato, Evento, GestorCidade, Imagem, PontoTuristico

GROUP_NAME = "Gestor de Cidade"

# (model, [codenames without the app-label prefix])
PERMISSION_MAP = {
  Cidade: ["view_cidade", "change_cidade"],  # no add/delete: they manage one existing city
  Evento: ["view_evento", "add_evento", "change_evento", "delete_evento"],
  PontoTuristico: [
    "view_pontoturistico",
    "add_pontoturistico",
    "change_pontoturistico",
    "delete_pontoturistico",
  ],
  Imagem: ["view_imagem", "add_imagem", "change_imagem", "delete_imagem"],
  Contato: ["view_contato", "add_contato", "change_contato", "delete_contato"],
}


class Command(BaseCommand):
  help = "Create/update the Gestor de Cidade group and provision a city-manager user."

  def add_arguments(self, parser):
    parser.add_argument("username")
    parser.add_argument("email")
    parser.add_argument("--cidade-slug", required=True)
    parser.add_argument(
      "--password",
      help="If omitted, you'll be prompted interactively.",
    )

  def handle(self, *args, **options):
    group = self._ensure_group()

    try:
      cidade = Cidade.objects.get(slug=options["cidade_slug"])
    except Cidade.DoesNotExist as exc:
      raise CommandError(f"No Cidade with slug={options['cidade_slug']!r}") from exc

    User = get_user_model()
    username = options["username"]
    password = options["password"]

    user, created = User.objects.get_or_create(
      username=username,
      defaults={"email": options["email"], "is_staff": True, "is_superuser": False},
    )
    if not created:
      user.is_staff = True
      user.is_superuser = False
      user.email = options["email"]

    if password:
      user.set_password(password)
    elif created:
      import getpass

      password = getpass.getpass(f"Password for {username}: ")
      user.set_password(password)

    user.save()
    user.groups.add(group)

    GestorCidade.objects.update_or_create(user=user, defaults={"cidade": cidade})

    self.stdout.write(
      self.style.SUCCESS(
        f"{'Created' if created else 'Updated'} user {username!r} as manager of {cidade}."
      )
    )

  def _ensure_group(self):
    group, _ = Group.objects.get_or_create(name=GROUP_NAME)
    wanted_permissions = []
    for model, codenames in PERMISSION_MAP.items():
      ct = ContentType.objects.get_for_model(model)
      wanted_permissions.extend(
        Permission.objects.filter(content_type=ct, codename__in=codenames)
      )
    group.permissions.set(wanted_permissions)
    return group
