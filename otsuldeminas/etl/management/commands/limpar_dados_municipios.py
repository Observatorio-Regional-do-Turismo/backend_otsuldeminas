from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cadastros.models import Municipio
from rais.models import EstoqueAnual, SaldoMensal, EstoqueMensal
from caged.models import SaldoMensalCaged


MODELOS = (
    EstoqueAnual,
    SaldoMensal,
    EstoqueMensal,
    SaldoMensalCaged,
)


class Command(BaseCommand):
    help = (
        "Remove dados RAIS/CAGED dos municípios informados, "
        "sem excluir os municípios."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--ibge",
            required=True,
            nargs="+",
            type=str,
            help="Códigos IBGE dos municípios a limpar.",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Executa a exclusão. Sem esta opção, apenas mostra as contagens.",
        )

    def handle(self, *args, **options):
        codigos_ibge = list(dict.fromkeys(options["ibge"]))

        existentes = set(
            Municipio.objects.filter(
                codigo_ibge__in=codigos_ibge
            ).values_list("codigo_ibge", flat=True)
        )
        inexistentes = sorted(set(codigos_ibge) - existentes)

        if inexistentes:
            raise CommandError(
                "Município(s) não encontrado(s): "
                + ", ".join(inexistentes)
            )

        if not options["confirm"]:
            self.stdout.write(
                f"Prévia para {len(codigos_ibge)} município(s): "
                + ", ".join(codigos_ibge)
            )

            for modelo in MODELOS:
                quantidade = modelo.objects.filter(
                    municipio_id__in=codigos_ibge
                ).count()
                self.stdout.write(
                    f"{modelo._meta.label}: {quantidade} registro(s)"
                )

            self.stdout.write(
                self.style.WARNING(
                    "Nenhum registro foi excluído. "
                    "Use --confirm para executar."
                )
            )
            return

        # As quatro operações são concluídas juntas ou revertidas juntas.
        with transaction.atomic():
            removidos = {}

            for modelo in MODELOS:
                quantidade, _ = modelo.objects.filter(
                    municipio_id__in=codigos_ibge
                ).delete()
                removidos[modelo._meta.label] = quantidade

        self.stdout.write(
            self.style.SUCCESS(
                "Limpeza concluída para: " + ", ".join(codigos_ibge)
            )
        )
        for nome_modelo, quantidade in removidos.items():
            self.stdout.write(
                f"{nome_modelo}: {quantidade} registro(s) removido(s)"
            )