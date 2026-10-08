from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from .models import Cidade, Estado, Evento, Noticia, PontoTuristico, IGR
from .serializers import CidadeDetailSerializer, CidadeSerializer, EstadoSerializer, EventoSerializer, NoticiaSerializer, PontoTuristicoSerializer, IGRSerializer
from .filters import CidadeFilter, EstadoFilter, EventoFilter, IGRFilter, NoticiaFilter, PontoTuristicoFilter


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


# NOTÍCIAS =============================================================================================================
class NoticiaViewSet(viewsets.ReadOnlyModelViewSet):
  queryset = Noticia.objects.select_related("cidade", "igr", "cidade__state").prefetch_related("image_relations").all()
  serializer_class = NoticiaSerializer
  filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
  filterset_class = NoticiaFilter
  search_fields = ["title", "summary", "content", "category", "author"]
  ordering_fields = ["published_at", "title"]
  ordering = ["-published_at", "-id"]