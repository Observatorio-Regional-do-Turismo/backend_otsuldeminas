from django.contrib import admin
from unfold.admin import ModelAdmin 
from .models import ArquivoColetado, LogOperacao

# Register your models here.
#admin.site.unregister(ArquivoColetado)
@admin.register(ArquivoColetado)
class ArquivoColetadoAdmin(ModelAdmin):
    list_display = ("nome", "ano", "mes", "status", "linhas_filtradas", "bytes", "short_msg")
    list_filter = ("status", "ano", "mes")
    search_fields = ("url", "path", "ano", "mes")
    ordering = ("nome", "ano")
    readonly_fields = ("bytes","linhas_filtradas","msg")

    @admin.display(description="msg")
    def short_msg(self, obj):
        return (obj.msg or "")[:90]
    
    # @admin.display(description="%")
    # def pct(self, obj: ArquivoColetado):
    #     p = obj.progresso_pct()
    #     return f"{p}%" if p is not None else "-"

    @admin.display(description="bytes")
    def bytes_fmt(self, obj: ArquivoColetado):
        return f"{obj.bytes:,}".replace(",", ".")

    @admin.display(description="esperado")
    def expected_fmt(self, obj: ArquivoColetado):
        return f"{obj.expected_bytes:,}".replace(",", ".") if obj.expected_bytes else "-"
    
    
@admin.register(LogOperacao)
class LogOperacaoAdmin(ModelAdmin):
    list_display = (
        "id",
        "systimestamp",
        "operacao",
        "arquivo",
        "data_referencia",
        "sucesso",
        "erro_resumido",
    )

    list_filter = (
        "sucesso",
        "operacao",
        "data_referencia",
        "systimestamp",
    )

    search_fields = (
        "operacao",
        "arquivo",
        "data_referencia",
        "erro",
    )
    
    readonly_fields = (
        "operacao",
        "arquivo",
        "data_referencia",
        "sucesso",
        "erro",
        "systimestamp",
    )

    date_hierarchy = "systimestamp"

    ordering = (
        "-systimestamp",
    )

    list_per_page = 50


    @admin.display(description="Erro")
    def erro_resumido(self, obj):
        if not obj.erro:
            return "-"

        limite = 100

        if len(obj.erro) <= limite:
            return obj.erro

        return f"{obj.erro[:limite]}..."

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
