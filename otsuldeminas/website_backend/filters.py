from django_filters import rest_framework as django_filters
from .models import Cidade, Estado, Evento, IGR, PontoTuristico


class EstadoFilter(django_filters.FilterSet):
  name = django_filters.CharFilter(lookup_expr="icontains")
  abbreviation = django_filters.CharFilter(lookup_expr="iexact")

  class Meta:
    model = Estado
    fields = ["name", "abbreviation"]


class IGRFilter(django_filters.FilterSet):
  name = django_filters.CharFilter(lookup_expr="icontains")

  class Meta:
    model = IGR
    fields = ["name"]


class CidadeFilter(django_filters.FilterSet):
  name = django_filters.CharFilter(lookup_expr="icontains")
  ibge_code = django_filters.CharFilter(lookup_expr="exact")
  estado = django_filters.CharFilter(field_name="state__slug", lookup_expr="exact")

  class Meta:
    model = Cidade
    fields = ["name", "ibge_code", "estado"]


class EventoFilter(django_filters.FilterSet):
  name = django_filters.CharFilter(lookup_expr="icontains")
  cidade = django_filters.CharFilter(field_name="cidade__slug", lookup_expr="exact")
  estado = django_filters.CharFilter(field_name="cidade__state__slug", lookup_expr="exact")
  ibge_code = django_filters.CharFilter(field_name="cidade__ibge_code", lookup_expr="exact")
  start_date = django_filters.IsoDateTimeFilter(lookup_expr="exact")
  end_date = django_filters.IsoDateTimeFilter(lookup_expr="exact")

  class Meta:
    model = Evento
    fields = ["name", "cidade", "estado", "ibge_code", "start_date", "end_date"]


class PontoTuristicoFilter(django_filters.FilterSet):
  name = django_filters.CharFilter(lookup_expr="icontains")
  cidade = django_filters.CharFilter(field_name="cidade__slug", lookup_expr="exact")
  estado = django_filters.CharFilter(field_name="cidade__state__slug", lookup_expr="exact")
  ibge_code = django_filters.CharFilter(field_name="cidade__ibge_code", lookup_expr="exact")

  class Meta:
    model = PontoTuristico
    fields = ["name", "cidade", "estado", "ibge_code"]