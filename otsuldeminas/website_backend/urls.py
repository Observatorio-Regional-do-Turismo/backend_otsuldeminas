from rest_framework.routers import DefaultRouter
from .views import CidadeViewSet, EstadoViewSet, EventoViewSet, PontoTuristicoViewSet, IGRViewSet

router = DefaultRouter()
router.register(r"estados", EstadoViewSet, basename="estado")
router.register(r"cidades", CidadeViewSet, basename="cidade")
router.register(r"igrs", IGRViewSet, basename="igr")
router.register(r"eventos", EventoViewSet, basename="evento")
router.register(r"pontos-turisticos", PontoTuristicoViewSet, basename="ponto-turistico")

urlpatterns = router.urls