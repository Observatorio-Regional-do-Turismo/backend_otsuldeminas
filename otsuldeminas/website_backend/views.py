from rest_framework import filters, viewsets

from .models import Cidade, Estado, Evento, PontoTuristico
from .serializers import (
  CidadeSerializer,
  EstadoSerializer,
  EventoSerializer,
  PontoTuristicoSerializer,
)


class EstadoViewSet(viewsets.ModelViewSet):
  queryset = Estado.objects.all()
  serializer_class = EstadoSerializer
  filter_backends = [filters.SearchFilter, filters.OrderingFilter]
  search_fields = ["name", "abbreviation"]
  ordering_fields = ["name"]


class CidadeViewSet(viewsets.ModelViewSet):
  queryset = Cidade.objects.select_related("state").all()
  serializer_class = CidadeSerializer
  filter_backends = [filters.SearchFilter, filters.OrderingFilter]
  search_fields = ["name", "ibge_code"]
  ordering_fields = ["name", "populacao", "hospedagens", "leitos"]

  def get_queryset(self):
    qs = super().get_queryset()
    estado_slug = self.request.query_params.get("estado")
    if estado_slug:
      qs = qs.filter(state__slug=estado_slug)
    return qs


class EventoViewSet(viewsets.ModelViewSet):
  queryset = Evento.objects.select_related("cidade", "cidade__state").all()
  serializer_class = EventoSerializer
  filter_backends = [filters.SearchFilter, filters.OrderingFilter]
  search_fields = ["name"]
  ordering_fields = ["start_date", "end_date"]

  def get_queryset(self):
    qs = super().get_queryset()
    cidade_slug = self.request.query_params.get("cidade")
    if cidade_slug:
      qs = qs.filter(cidade__slug=cidade_slug)
    return qs


class PontoTuristicoViewSet(viewsets.ModelViewSet):
  queryset = PontoTuristico.objects.select_related("cidade", "cidade__state").all()
  serializer_class = PontoTuristicoSerializer
  filter_backends = [filters.SearchFilter, filters.OrderingFilter]
  search_fields = ["name"]
  ordering_fields = ["name"]

  def get_queryset(self):
    qs = super().get_queryset()
    cidade_slug = self.request.query_params.get("cidade")
    if cidade_slug:
      qs = qs.filter(cidade__slug=cidade_slug)
    return qs
