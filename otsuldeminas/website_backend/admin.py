from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline

from .models import Cidade, Contato, Estado, Evento, GestorCidade, Imagem, PontoTuristico


class ImagemInline(GenericTabularInline):
  model = Imagem
  extra = 1
  fields = ("image", "alt_text", "caption", "order", "is_cover")
  ordering = ("order",)


class ContatoInline(GenericTabularInline):
  model = Contato
  extra = 1
  fields = ("type", "label", "value", "address", "latitude", "longitude", "order")
  ordering = ("order",)


class CityScopedAdminMixin:
  cidade_lookup = "cidade"

  def _managed_cidade(self, request):
    if request.user.is_superuser:
      return None  # not restricted
    try:
      return request.user.gestor_cidade.cidade
    except GestorCidade.DoesNotExist:
      return None

  def get_queryset(self, request):
    qs = super().get_queryset(request)
    if request.user.is_superuser:
      return qs
    cidade = self._managed_cidade(request)
    if cidade is None:
      return qs.none()
    if self.cidade_lookup == "pk":
      return qs.filter(pk=cidade.pk)
    return qs.filter(**{self.cidade_lookup: cidade})

  def _obj_matches_managed_cidade(self, request, obj):
    cidade = self._managed_cidade(request)
    if cidade is None:
      return False
    obj_cidade = obj if self.cidade_lookup == "pk" else getattr(obj, self.cidade_lookup, None)
    return obj_cidade == cidade

  def has_change_permission(self, request, obj=None):
    if request.user.is_superuser or obj is None:
      return super().has_change_permission(request, obj)
    return super().has_change_permission(request, obj) and self._obj_matches_managed_cidade(request, obj)

  def has_delete_permission(self, request, obj=None):
    if request.user.is_superuser or obj is None:
      return super().has_delete_permission(request, obj)
    return super().has_delete_permission(request, obj) and self._obj_matches_managed_cidade(request, obj)


@admin.register(Estado)
class EstadoAdmin(admin.ModelAdmin):
  # Superuser-only: city managers are never granted permissions on this
  # model (see the Group setup below), so it won't even appear for them.
  list_display = ("name", "abbreviation", "slug")
  search_fields = ("name", "abbreviation")
  prepopulated_fields = {"slug": ("name",)}
  inlines = [ImagemInline, ContatoInline]


@admin.register(Cidade)
class CidadeAdmin(CityScopedAdminMixin, admin.ModelAdmin):
  cidade_lookup = "pk"

  list_display = ("name", "state", "populacao", "hospedagens", "pib", "slug")
  list_filter = ("state",)
  search_fields = ("name", "ibge_code")
  prepopulated_fields = {"slug": ("name",)}
  autocomplete_fields = ("state",)
  inlines = [ImagemInline, ContatoInline]

  def has_add_permission(self, request):
    # Only superusers create new cities; a city manager just edits theirs.
    return request.user.is_superuser

  def get_readonly_fields(self, request, obj=None):
    return (
      "state",
      "slug",
      "ibge_code",
      "hospedagens",
      "restaurantes",
      "populacao",
      "pib",
    )


@admin.register(Evento)
class EventoAdmin(CityScopedAdminMixin, admin.ModelAdmin):
  cidade_lookup = "cidade"

  list_display = ("name", "cidade", "start_date", "end_date")
  list_filter = ("cidade__state", "cidade")
  search_fields = ("name",)
  prepopulated_fields = {"slug": ("name",)}
  autocomplete_fields = ("cidade",)
  date_hierarchy = "start_date"
  inlines = [ImagemInline, ContatoInline]

  def has_add_permission(self, request):
    if request.user.is_superuser:
      return True
    return self._managed_cidade(request) is not None

  def get_form(self, request, obj=None, **kwargs):
    form = super().get_form(request, obj, **kwargs)
    cidade = self._managed_cidade(request)
    if cidade is not None and "cidade" in form.base_fields:
      # Lock the FK to their own city instead of letting them pick.
      form.base_fields["cidade"].queryset = Cidade.objects.filter(pk=cidade.pk)
      form.base_fields["cidade"].initial = cidade
      form.base_fields["cidade"].disabled = True
    return form

  def save_model(self, request, obj, form, change):
    cidade = self._managed_cidade(request)
    if cidade is not None:
      obj.cidade = cidade  # belt-and-suspenders against tampering
    super().save_model(request, obj, form, change)


@admin.register(PontoTuristico)
class PontoTuristicoAdmin(CityScopedAdminMixin, admin.ModelAdmin):
  cidade_lookup = "cidade"

  list_display = ("name", "cidade", "slug")
  list_filter = ("cidade__state", "cidade")
  search_fields = ("name",)
  prepopulated_fields = {"slug": ("name",)}
  autocomplete_fields = ("cidade",)
  inlines = [ImagemInline, ContatoInline]

  def has_add_permission(self, request):
    if request.user.is_superuser:
      return True
    return self._managed_cidade(request) is not None

  def get_form(self, request, obj=None, **kwargs):
    form = super().get_form(request, obj, **kwargs)
    cidade = self._managed_cidade(request)
    if cidade is not None and "cidade" in form.base_fields:
      form.base_fields["cidade"].queryset = Cidade.objects.filter(pk=cidade.pk)
      form.base_fields["cidade"].initial = cidade
      form.base_fields["cidade"].disabled = True
    return form

  def save_model(self, request, obj, form, change):
    cidade = self._managed_cidade(request)
    if cidade is not None:
      obj.cidade = cidade
    super().save_model(request, obj, form, change)


@admin.register(GestorCidade)
class GestorCidadeAdmin(admin.ModelAdmin):
  # Superuser-only: this is how you assign a manager to a city.
  list_display = ("user", "cidade")
  autocomplete_fields = ("user", "cidade")

  def has_module_permission(self, request):
    return request.user.is_superuser

  def has_view_permission(self, request, obj=None):
    return request.user.is_superuser

  def has_add_permission(self, request):
    return request.user.is_superuser

  def has_change_permission(self, request, obj=None):
    return request.user.is_superuser

  def has_delete_permission(self, request, obj=None):
    return request.user.is_superuser
