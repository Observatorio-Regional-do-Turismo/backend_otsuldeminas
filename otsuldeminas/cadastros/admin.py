from django.contrib import admin
from unfold.admin import ModelAdmin 
from .models import Municipio, CNAE
from rais.models import EstoqueAnual, SaldoMensal, EstoqueMensal
from caged.models import SaldoMensalCaged
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.core.management import call_command
from django.core.management.base import CommandError
from django.template.response import TemplateResponse
from io import StringIO
from django.contrib import admin, messages

#admin.site.unregister(Municipio)
#admin.site.unregister(CNAE)
@admin.register(Municipio)
class MunicipioAdmin(ModelAdmin):
    list_display = ("nome","codigo_ibge","codigo_receita_federal")
    list_filter = ("nome",)
    search_fields = ("nome", "codigo_ibge","codigo_receita_federal")
    ordering = ("nome",)
    
    actions = ["nivelar_municipios", "limpar_dados_municipios"]

    @admin.action(
        description="Nivelar municípios selecionados (RAIS + CAGED)",
        permissions=["change"],
    )
    def nivelar_municipios(self, request, queryset):
        codigos_ibge = list(
            queryset.order_by("codigo_ibge").values_list(
                "codigo_ibge", flat=True
            )
        )

        try:
            call_command(
                "nivelar_municipio_rais_caged",
                ibge=codigos_ibge,
            )
        except CommandError as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
            return

        self.message_user(
            request,
            f"Uma chain de nivelamento foi disparada para "
            f"{len(codigos_ibge)} município(s). "
            "O processamento continuará no Celery.",
            level=messages.SUCCESS,
        )
        
    @admin.action(
    description="Limpar dados RAIS/CAGED dos municípios selecionados",
    permissions=["delete"],
    )
    def limpar_dados_municipios(self, request, queryset):
        modelos = (
            EstoqueAnual,
            SaldoMensal,
            EstoqueMensal,
            SaldoMensalCaged,
        )

        # A action apaga dados de outros modelos, então confira também
        # as permissões de exclusão nesses modelos.
        sem_permissao = [
            modelo._meta.label
            for modelo in modelos
            if not request.user.has_perm(
                f"{modelo._meta.app_label}."
                f"delete_{modelo._meta.model_name}"
            )
        ]

        if sem_permissao:
            self.message_user(
                request,
                "Sem permissão para excluir dados de: "
                + ", ".join(sem_permissao),
                level=messages.ERROR,
            )
            return

        codigos_ibge = list(
            queryset.order_by("codigo_ibge").values_list(
                "codigo_ibge", flat=True
            )
        )

        if not codigos_ibge:
            self.message_user(
                request,
                "Nenhum município selecionado.",
                level=messages.WARNING,
            )
            return

        if request.POST.get("confirmar_limpeza") != "sim":
            contagens = [
                (
                    modelo._meta.verbose_name_plural,
                    modelo.objects.filter(
                        municipio_id__in=codigos_ibge
                    ).count(),
                )
                for modelo in modelos
            ]

            context = {
                **self.admin_site.each_context(request),
                "title": "Confirmar limpeza dos municípios",
                "opts": self.model._meta,
                "municipios": list(queryset.order_by("nome")),
                "codigos_ibge": codigos_ibge,
                "contagens": contagens,
                "action_name": "limpar_dados_municipios",
                "action_checkbox_name": ACTION_CHECKBOX_NAME,
            }
            return TemplateResponse(
                request,
                "admin/cadastros/municipio/confirmar_limpeza.html",
                context,
            )

        saida = StringIO()

        try:
            call_command(
                "limpar_dados_municipios",
                ibge=codigos_ibge,
                confirm=True,
                stdout=saida,
            )
        except CommandError as exc:
            self.message_user(
                request, str(exc), level=messages.ERROR
            )
            return

        self.message_user(
            request,
            saida.getvalue().strip(),
            level=messages.SUCCESS,
        )

@admin.register(CNAE)
class CNAEAdmin(ModelAdmin):
    list_display = ("descricao", "codigo", "classificacao_otmg")
    search_fields = ("codigo", "descricao", "classificacao_otmg")
    ordering = ("codigo",)
# Register your models here.
