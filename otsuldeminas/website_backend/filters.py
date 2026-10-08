from django_filters import rest_framework as django_filters
from .models import Cidade, Estado, Evento, IGR, Noticia, PontoTuristico


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
  estado = django_filters.CharFilter(field_name="state__id", lookup_expr="exact")
  igr = django_filters.CharFilter(field_name="igr__id", lookup_expr="exact")

  class Meta:
    model = Cidade
    fields = ["name", "ibge_code", "estado"]


class EventoFilter(django_filters.FilterSet):
  name = django_filters.CharFilter(lookup_expr="icontains")
  cidade = django_filters.CharFilter(field_name="cidade__id", lookup_expr="exact")
  estado = django_filters.CharFilter(field_name="cidade__state__id", lookup_expr="exact")
  igr = django_filters.CharFilter(field_name="cidade__igr__id", lookup_expr="exact")
  ibge_code = django_filters.CharFilter(field_name="cidade__ibge_code", lookup_expr="exact")
  start_date = django_filters.IsoDateTimeFilter(lookup_expr="exact")
  end_date = django_filters.IsoDateTimeFilter(lookup_expr="exact")
  start_after = django_filters.IsoDateTimeFilter(field_name="start_date", lookup_expr="gte")
  start_before = django_filters.IsoDateTimeFilter(field_name="start_date", lookup_expr="lte")
  end_after = django_filters.IsoDateTimeFilter(field_name="end_date", lookup_expr="gte")
  end_before = django_filters.IsoDateTimeFilter(field_name="end_date", lookup_expr="lte")

  class Meta:
    model = Evento
    fields = [
      "name", "cidade", "estado", "ibge_code", "start_date", "end_date",
      "start_after", "start_before", "end_after", "end_before",
    ]


class PontoTuristicoFilter(django_filters.FilterSet):
  name = django_filters.CharFilter(lookup_expr="icontains")
  cidade = django_filters.CharFilter(field_name="cidade__id", lookup_expr="exact")
  estado = django_filters.CharFilter(field_name="cidade__state__id", lookup_expr="exact")
  igr = django_filters.CharFilter(field_name="cidade__igr__id", lookup_expr="exact")
  ibge_code = django_filters.CharFilter(field_name="cidade__ibge_code", lookup_expr="exact")

  class Meta:
    model = PontoTuristico
    fields = ["name", "cidade", "estado", "ibge_code"]


class NoticiaFilter(django_filters.FilterSet):
  title = django_filters.CharFilter(lookup_expr="icontains")
  category = django_filters.CharFilter(lookup_expr="icontains")
  cidade = django_filters.NumberFilter(field_name="cidade__id")
  igr = django_filters.NumberFilter(field_name="igr__id")
  estado = django_filters.NumberFilter(field_name="cidade__state__id")
  is_featured = django_filters.BooleanFilter()
  published_after = django_filters.IsoDateTimeFilter(field_name="published_at", lookup_expr="gte")
  published_before = django_filters.IsoDateTimeFilter(field_name="published_at", lookup_expr="lte")

  class Meta:
    model = Noticia
    fields = [
      "title", "category", "cidade", "igr", "estado", "is_featured",
      "published_after", "published_before",
    ]