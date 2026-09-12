from django.db import models

# Create your models here.
class ArquivoColetado(models.Model):
    ARQ_STATUS = [
        ("PENDING", "Pendente"),
        ("DOWNLOADED", "Baixado"),
        ("EXTRACTED", "Extraído"),
        ("FILTERED", "Filtrado"),
        ("LOADED", "Carregado"),
        ("FAILED", "Falhou"),
    ]
    id = models.BigAutoField(primary_key=True)
    nome = models.CharField(max_length=50, default="")  # 0..9d()
    ano = models.IntegerField(default=0)
    mes = models.IntegerField(default=0)
    path_zip = models.TextField(blank=True, default="")
    path_extraido= models.TextField(blank=True, default="")
    path_filtrado= models.TextField(blank=True, default="")
    #sha256 = models.CharField(max_length=64, blank=True, default="")
    bytes = models.BigIntegerField(default=0)
    status = models.CharField(max_length=10, choices=ARQ_STATUS, default="PENDING")
    linhas_filtradas = models.BigIntegerField(default=0)
    msg = models.TextField(blank=True, default="")
    expected_bytes = models.BigIntegerField(blank=True, null=True)

    class Meta:
        #unique_together = [("coleta", "nome")]
        ordering = ["nome"]

    # def progresso_pct(self) -> float | None:
    #     if self.expected_bytes and self.bytes:
    #         return round(self.bytes / self.expected_bytes * 100, 1)
    #     return None
    def __str__(self):
        return f"{self.nome}.zip"


class LogOperacao(models.Model):
    operacao = models.CharField(
        max_length=30,
    )

    arquivo = models.CharField(
        max_length=50,
    )

    data_referencia = models.CharField(
        max_length=15,
    )

    sucesso = models.BooleanField(
        default=False,
    )

    erro = models.TextField(
        blank=True,
        default="",
    )

    systimestamp = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "log_operacao"
        ordering = ["-systimestamp"]
        verbose_name = "Log de operação"
        verbose_name_plural = "Logs de operação"

    def __str__(self):
        return (
            f"{self.operacao} - "
            f"{self.arquivo} - "
            f"{self.data_referencia}"
        )