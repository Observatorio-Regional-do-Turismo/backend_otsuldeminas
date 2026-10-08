import json

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import GestorCidade, GestorIGR


def get_manager_scopes(user):
  try:
    cidade = user.gestor_cidade.cidade
  except GestorCidade.DoesNotExist:
    cidade = None

  try:
    igr = user.gestor_igr.igr
  except GestorIGR.DoesNotExist:
    igr = None

  return cidade, igr


def manager_payload(user):
  cidade, igr = get_manager_scopes(user)
  scopes = []
  if cidade is not None:
    scopes.append({
      "type": "cidade",
      "id": cidade.pk,
      "name": cidade.name,
      "slug": cidade.slug,
    })
  if igr is not None:
    scopes.append({
      "type": "igr",
      "id": igr.pk,
      "name": igr.name,
      "slug": igr.slug,
    })
  return {
    "username": user.get_username(),
    "scopes": scopes,
  }


@ensure_csrf_cookie
@require_GET
def csrf_token(request):
  return JsonResponse({"csrfToken": get_token(request)})


@require_POST
@csrf_protect
def manager_login(request):
  try:
    payload = json.loads(request.body)
  except (json.JSONDecodeError, UnicodeDecodeError):
    return JsonResponse({"detail": "Corpo JSON inválido."}, status=400)

  if not isinstance(payload, dict):
    return JsonResponse({"detail": "Corpo JSON inválido."}, status=400)

  username = payload.get("username")
  password = payload.get("password")
  if not isinstance(username, str) or not isinstance(password, str) or not username or not password:
    return JsonResponse({"detail": "Informe usuário e senha."}, status=400)

  user = authenticate(request, username=username, password=password)
  if user is None or not user.is_active:
    return JsonResponse({"detail": "Credenciais inválidas ou usuário sem acesso."}, status=401)

  if not any(get_manager_scopes(user)):
    return JsonResponse({"detail": "Credenciais inválidas ou usuário sem acesso."}, status=401)

  login(request, user)
  return JsonResponse(manager_payload(user))


@require_POST
@csrf_protect
def manager_logout(request):
  logout(request)
  return JsonResponse({}, status=200)


@require_GET
def manager_session(request):
  if not request.user.is_authenticated:
    return JsonResponse({"detail": "Autenticação necessária."}, status=401)
  if not any(get_manager_scopes(request.user)):
    return JsonResponse({"detail": "Este usuário não possui acesso à gestão."}, status=403)
  return JsonResponse(manager_payload(request.user))
