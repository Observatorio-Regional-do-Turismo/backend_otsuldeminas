from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management import BaseCommand, CommandError
from django.db import transaction

from website_backend.models import Cidade, GestorCidade, GestorIGR, IGR


class Command(BaseCommand):
  help = "Provision a city or IGR manager account; public registration is not available."

  def add_arguments(self, parser):
    parser.add_argument("tipo", choices=["cidade", "igr"])
    parser.add_argument("username")
    parser.add_argument("email")
    parser.add_argument("slug", help="Slug of the City or IGR assigned to this manager.")

  def handle(self, *args, **options):
    tipo = options["tipo"]
    scope_model, manager_model, relation_name = (
      (Cidade, GestorCidade, "cidade") if tipo == "cidade"
      else (IGR, GestorIGR, "igr")
    )

    try:
      scope = scope_model.objects.get(slug=options["slug"])
    except scope_model.DoesNotExist as exc:
      raise CommandError(f"No {scope_model.__name__} with slug={options['slug']!r}.") from exc

    User = get_user_model()
    user = User.objects.filter(username=options["username"]).first()
    if user is not None and user.is_superuser:
      raise CommandError("A superuser account cannot be assigned as a manager.")
    if user is not None and user.is_staff:
      raise CommandError("Use a dedicated non-staff account for the manager portal.")

    existing_assignment = manager_model.objects.filter(user=user).first() if user else None
    if existing_assignment and getattr(existing_assignment, relation_name) != scope:
      raise CommandError(
        f"This user already manages another {tipo}; reassign it explicitly in Django admin."
      )

    password = getpass(f"Senha para {options['username']}: ")
    confirmation = getpass("Confirme a senha: ")
    if password != confirmation:
      raise CommandError("As senhas não coincidem.")
    if not password:
      raise CommandError("A senha não pode ficar vazia.")

    if user is None:
      user = User(username=options["username"], email=options["email"])
    else:
      user.email = options["email"]

    try:
      validate_password(password, user=user)
    except ValidationError as exc:
      raise CommandError("; ".join(exc.messages)) from exc

    with transaction.atomic():
      user.set_password(password)
      user.save()
      manager_model.objects.update_or_create(
        user=user,
        defaults={relation_name: scope},
      )
    self.stdout.write(
      self.style.SUCCESS(f"Manager {user.get_username()!r} assigned to {scope}.")
    )
