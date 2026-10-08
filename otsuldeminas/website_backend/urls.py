from rest_framework.routers import DefaultRouter
from .views import CidadeViewSet, EstadoViewSet, EventoViewSet, NoticiaViewSet, PontoTuristicoViewSet, IGRViewSet
from .manager_auth import csrf_token, manager_login, manager_logout, manager_session
from .manager_views import ManagerCityViewSet, ManagerIGRViewSet, ManagerNoticiaViewSet
from django.urls import path

router = DefaultRouter()
router.register(r"estados", EstadoViewSet, basename="estado")
router.register(r"cidades", CidadeViewSet, basename="cidade")
router.register(r"igrs", IGRViewSet, basename="igr")
router.register(r"eventos", EventoViewSet, basename="evento")
router.register(r"pontos-turisticos", PontoTuristicoViewSet, basename="ponto-turistico")
router.register(r"noticias", NoticiaViewSet, basename="noticia")
router.register(r"gestao/cidades", ManagerCityViewSet, basename="gestao-cidade")
router.register(r"gestao/igrs", ManagerIGRViewSet, basename="gestao-igr")
router.register(r"gestao/noticias", ManagerNoticiaViewSet, basename="gestao-noticia")

urlpatterns = [
  path("auth/csrf/", csrf_token, name="manager-csrf"),
  path("auth/login/", manager_login, name="manager-login"),
  path("auth/logout/", manager_logout, name="manager-logout"),
  path("auth/session/", manager_session, name="manager-session"),
] + router.urls