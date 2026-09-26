"""
management/commands/nivelar_municipio_rais_caged.py

Nivela UM único município (por código IBGE) contra toda a série histórica já
existente na base: primeiro roda o RAIS ano a ano (do ano mais antigo ao mais
recente já presentes na base, olhando EstoqueAnual/SaldoMensal em geral, não
filtrado pelo município -- esses dados ainda não existem para a cidade nova,
é justamente isso que estamos populando), e só depois roda o CAGED mês a mês,
dos meses "adjacentes" que ficaram entre o último ano do RAIS e o mês mais
recente já coletado do CAGED.

Por que só 1 município por execução: conforme combinado, para não poluir a
função com um for aninhado (RAIS anos x CAGED meses x municípios), o comando
roda para um único codigo_ibge por chamada. Para várias cidades, rode o
comando várias vezes (ou faça um wrapper simples que itera e chama este
comando/celery para cada uma).

Execução 100% linear: tudo roda dentro de uma ÚNICA chain do Celery
(RAIS ano 1 -> RAIS ano 2 -> ... -> RAIS ano N -> CAGED mes 1 -> ... -> CAGED
mes M -> finalização), pois cada etapa depende do estado deixado pela
anterior:
  - Dentro do RAIS: carregar_saldos_mensais(year) usa EstoqueAnual do
    ano anterior (year - 1), então os anos têm que rodar em ordem.
  - Entre RAIS e CAGED: quando o CAGED começa a rodar para o município novo,
    ele precisa que o EstoqueMensal de dezembro do último ano RAIS já exista
    (carregar_saldos_mensais_temporarios do CAGED olha o mês anterior).

USO:
    python manage.py nivelar_municipio_rais_caged --ibge 3170206

    # Sem disparar de fato, só para inspecionar o plano de execução:
    python manage.py nivelar_municipio_rais_caged --ibge 3170206 --dry-run
"""

from datetime import date

from dateutil.relativedelta import relativedelta
from celery import chain
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max, Min

from rais.models import EstoqueAnual
from caged.models import SaldoMensalCaged
from rais.tasks import task_coletar_arquivos_rais
from caged.tasks import task_coletar_arquivos_caged


class Command(BaseCommand):
    help = (
        "Nivela um único município (código IBGE) contra toda a série "
        "histórica: roda o RAIS ano a ano e, em seguida, o CAGED mês a mês "
        "para os meses posteriores ao último ano RAIS, em uma única chain "
        "linear do Celery."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--ibge",
            required=True,
            type=str,
            help="Código IBGE do município a nivelar (um único município por execução).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Apenas exibe o plano de execução (anos RAIS e meses CAGED), sem disparar nada.",
        )

    def handle(self, *args, **options):
        codigo_ibge = options["ibge"]

        anos_rais = self._descobrir_anos_rais()
        meses_caged = self._descobrir_meses_caged_adjacentes(ano_final_rais=anos_rais[-1])

        self.stdout.write(f"Município: {codigo_ibge}")
        self.stdout.write(f"Anos RAIS a processar (em ordem): {anos_rais}")
        self.stdout.write(f"Meses CAGED a processar (em ordem): {meses_caged}")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry-run: nenhuma task disparada."))
            return

        async_result = self._disparar_chain(codigo_ibge, anos_rais, meses_caged)
        self.stdout.write(
            self.style.SUCCESS(
                f"Chain de nivelamento disparada para o município {codigo_ibge}: {async_result.id}"
            )
        )

    def _descobrir_anos_rais(self):
        """
        Intervalo de anos já cobertos pela base RAIS (olhando a base como um
        todo, não o município novo -- que ainda não tem nenhum registro).
        """
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
        """
        Meses de CAGED entre janeiro do ano seguinte ao último ano do RAIS
        e o mês/ano mais recente já coletado de CAGED (base como um todo).
        """
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

    def _disparar_chain(self, codigo_ibge, anos_rais, meses_caged):
        etapas = []

        for ano in anos_rais:
            etapas.append(
                task_coletar_arquivos_rais.si(ano=ano, codigo_ibge=codigo_ibge)
            )

        for ano, mes in meses_caged:
            etapas.append(
                task_coletar_arquivos_caged.si(ano=ano, mes=mes, codigo_ibge=codigo_ibge)
            )

        if not etapas:
            raise CommandError("Nenhuma etapa (RAIS ou CAGED) a executar para este município.")

        return chain(*etapas).apply_async()