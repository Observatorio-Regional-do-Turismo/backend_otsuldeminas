from datetime import date

from dateutil.relativedelta import relativedelta
from celery import chain
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max, Min

from rais.models import EstoqueAnual, EstoqueMensal, SaldoMensal
from caged.models import SaldoMensalCaged

from etl.tasks import (
    task_coletar_vinc_pub,
    task_coletar_estab_pub,
    task_carregar_saldos_mensais,
    task_finalizar_coleta_rais,
    task_coletar_caged_mov,
    task_coletar_caged_for,
    task_coletar_caged_exc,
    task_carregar_saldos_mensais_temporarios,
    task_finalizar_coleta_caged,
)


class Command(BaseCommand):
    help = (
        "Nivela um único município (código IBGE) contra toda a série "
        "histórica: roda o RAIS ano a ano e, em seguida, o CAGED mês a mês "
        "para os meses posteriores ao último ano RAIS, em uma única chain "
        "linear (achatada) do Celery, usando diretamente as tasks atômicas."
    )

    def add_arguments(self, parser):
        parser.add_argument(
        "--ibge",
        required=True,
        nargs="+",
        type=str,
        help="Um ou mais códigos IBGE dos municípios a nivelar.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Apenas exibe o plano de execução (anos RAIS e meses CAGED), sem disparar nada.",
        )
    
    def handle(self, *args, **options):
        codigos_ibge = list(dict.fromkeys(options["ibge"]))

        anos_rais = self._descobrir_anos_rais()
        meses_caged = self._descobrir_meses_caged_adjacentes(
            ano_final_rais=anos_rais[-1]
        )

        self.stdout.write(f"Municípios: {codigos_ibge}")
        self.stdout.write(f"Anos RAIS a processar: {anos_rais}")
        self.stdout.write(f"Meses CAGED a processar: {meses_caged}")

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING("Dry-run: nenhuma task disparada.")
            )
            return
        
        self._validar_municipios_sem_dados(codigos_ibge)

        async_result = self._disparar_chain(
            codigos_ibge, anos_rais, meses_caged
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Chain de nivelamento disparada para {codigos_ibge}: "
                f"{async_result.id}"
            )
        )
    
    def _validar_municipios_sem_dados(self, codigos_ibge):
        modelos = (
            EstoqueAnual,
            EstoqueMensal,
            SaldoMensal,
            SaldoMensalCaged,
        )

        encontrados = {}

        for modelo in modelos:
            codigos_com_dados = (
                modelo.objects
                .filter(municipio_id__in=codigos_ibge)
                .values_list("municipio_id", flat=True)
                .distinct()
            )

            for codigo in codigos_com_dados:
                encontrados.setdefault(codigo, []).append(
                    modelo._meta.verbose_name
                )

        if encontrados:
            detalhes = "; ".join(
                f"{codigo}: {', '.join(modelos_encontrados)}"
                for codigo, modelos_encontrados in sorted(encontrados.items())
            )

            raise CommandError(
                "Nivelamento não iniciado. Há municípios com dados "
                "já existentes: "
                f"{detalhes}. "
                "Execute a limpeza desses municípios antes de nivelar."
            )

    def _descobrir_anos_rais(self):
        limites = EstoqueAnual.objects.aggregate(
            ano_min=Min("referencia"),
            ano_max=Max("referencia"),
        )
        if limites["ano_min"] is None or limites["ano_max"] is None:
            raise CommandError("Não há nenhum EstoqueAnual na base para servir de referência de anos do RAIS.")

        ano_inicio = limites["ano_min"].year
        ano_fim = limites["ano_max"].year
        return list(range(ano_inicio, ano_fim + 1))

    def _descobrir_meses_caged_adjacentes(self, ano_final_rais):
        referencia_caged = SaldoMensalCaged.objects.aggregate(
            ultima=Max("referencia")
        )["ultima"]

        if referencia_caged is None:
            raise CommandError("Não há nenhum SaldoMensalCaged na base para servir de referência do CAGED.")

        inicio = date(ano_final_rais + 1, 1, 1)
        fim = referencia_caged.replace(day=1)

        if inicio > fim:
            return []

        meses = []
        atual = inicio
        while atual <= fim:
            meses.append((atual.year, atual.month))
            atual += relativedelta(months=1)
        return meses

    def _disparar_chain(self, codigos_ibge, anos_rais, meses_caged):
        etapas = []

        for ano in anos_rais:
            etapas.extend([
                task_coletar_vinc_pub.si(
                    ano=ano, codigo_ibge=codigos_ibge
                ),
                task_coletar_estab_pub.si(
                    ano=ano, codigo_ibge=codigos_ibge
                ),
                task_carregar_saldos_mensais.si(
                    ano=ano, codigo_ibge=codigos_ibge
                ),
                task_finalizar_coleta_rais.si(ano=ano),
            ])

        for ano, mes in meses_caged:
            etapas.extend([
                task_coletar_caged_mov.si(
                    ano=ano, mes=mes, codigo_ibge=codigos_ibge
                ),
                task_coletar_caged_for.si(
                    ano=ano, mes=mes, codigo_ibge=codigos_ibge
                ),
                task_coletar_caged_exc.si(
                    ano=ano, mes=mes, codigo_ibge=codigos_ibge
                ),
                task_carregar_saldos_mensais_temporarios.si(
                    year=ano, month=mes, codigo_ibge=codigos_ibge
                ),
                task_finalizar_coleta_caged.si(ano=ano, mes=mes),
            ])

        if not etapas:
            raise CommandError(
                "Nenhuma etapa (RAIS ou CAGED) a executar."
            )

        return chain(*etapas).apply_async()