from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from .models import Cidade, Estado, Evento, PontoTuristico, IGR
from .serializers import CidadeDetailSerializer, CidadeSerializer, EstadoSerializer, EventoSerializer, PontoTuristicoSerializer, IGRSerializer
from .filters import CidadeFilter, EstadoFilter, EventoFilter, IGRFilter, PontoTuristicoFilter


# ESTADOS ==============================================================================================================
class EstadoViewSet(viewsets.ReadOnlyModelViewSet):
  queryset = Estado.objects.all()
  serializer_class = EstadoSerializer
  filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
  filterset_class = EstadoFilter
  ordering_fields = ["name"]


# IGRs ==============================================================================================================
class IGRViewSet(viewsets.ReadOnlyModelViewSet):
  queryset = IGR.objects.all()
  serializer_class = IGRSerializer
  filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
  filterset_class = IGRFilter
  ordering_fields = ["name"]


# CIDADES ==============================================================================================================
class CidadeViewSet(viewsets.ReadOnlyModelViewSet):
  queryset = Cidade.objects.select_related("state").all()
  serializer_class = CidadeSerializer
  filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
  filterset_class = CidadeFilter
  ordering_fields = ["name"]

  def get_serializer_class(self):
    if self.action == "retrieve":
      return CidadeDetailSerializer
    return CidadeSerializer


# EVENTOS ==============================================================================================================
class EventoViewSet(viewsets.ReadOnlyModelViewSet):
  queryset = Evento.objects.select_related("cidade", "cidade__state").all()
  serializer_class = EventoSerializer
  filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
  filterset_class = EventoFilter
  ordering_fields = ["cidade", "start_date", "name"]


# PONTOS TURÍSTICOS ====================================================================================================
class PontoTuristicoViewSet(viewsets.ReadOnlyModelViewSet):
  queryset = PontoTuristico.objects.select_related("cidade", "cidade__state",).all()
  serializer_class = PontoTuristicoSerializer
  filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
  filterset_class = PontoTuristicoFilter
  ordering_fields = ["cidade", "name"]