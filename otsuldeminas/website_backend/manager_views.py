from django.db.models import Q
from rest_framework import permissions, viewsets
from rest_framework.authentication import SessionAuthentication

from .manager_auth import get_manager_scopes
from .manager_serializers import ManagerCitySerializer, ManagerIGRSerializer, ManagerNoticiaSerializer
from .models import Cidade, IGR, Noticia


class IsAssignedManager(permissions.BasePermission):
  def has_permission(self, request, _view):
    if not request.user or not request.user.is_authenticated:
      return False
    return any(get_manager_scopes(request.user))


class ManagerViewSet(viewsets.ModelViewSet):
  authentication_classes = [SessionAuthentication]
  permission_classes = [permissions.IsAuthenticated, IsAssignedManager]


class ManagerCityViewSet(ManagerViewSet):
  serializer_class = ManagerCitySerializer
  http_method_names = ["get", "patch", "head", "options"]

  def get_queryset(self):
    city, _ = get_manager_scopes(self.request.user)
    if city is None:
      return Cidade.objects.none()
    return Cidade.objects.filter(pk=city.pk).select_related("state")


class ManagerIGRViewSet(ManagerViewSet):
  serializer_class = ManagerIGRSerializer
  http_method_names = ["get", "patch", "head", "options"]

  def get_queryset(self):
    _, igr = get_manager_scopes(self.request.user)
    if igr is None:
      return IGR.objects.none()
    return IGR.objects.filter(pk=igr.pk)


class ManagerNoticiaViewSet(ManagerViewSet):
  serializer_class = ManagerNoticiaSerializer

  def get_queryset(self):
    city, igr = get_manager_scopes(self.request.user)
    scope = Q()
    if city is not None:
      scope |= Q(cidade_id=city.pk)
    if igr is not None:
      scope |= Q(igr_id=igr.pk) | Q(cidade__igr_id=igr.pk)
    return Noticia.objects.filter(scope).select_related("cidade", "igr")
