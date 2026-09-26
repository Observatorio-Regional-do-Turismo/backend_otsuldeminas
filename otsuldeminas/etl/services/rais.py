from ftplib import FTP
from django.conf import settings
from django.db.models import F
from etl.models import ArquivoColetado
from cadastros.models import CNAE, Municipio
from rais.models import EstoqueAnual, SaldoMensal, EstoqueMensal
import os
import py7zr
import pathlib
import pandas as pd
import calendar
from datetime import date
from itertools import product


BASE_DIR = pathlib.Path(settings.BASE_DIR)
DATA_DIR = BASE_DIR / "data" / "rais"

def gerar_ultimo_dia(ano, mes):
    _, ultimo_dia = calendar.monthrange(ano, mes)
    return date(ano,mes,ultimo_dia)

def _normalizar_ibge(codigo_ibge):
    if codigo_ibge is None:
        return None
    if isinstance(codigo_ibge, (list, tuple, set)):
        return [str(c) for c in codigo_ibge]
    return [str(codigo_ibge)]

def baixar_rais(arquivoColetado: ArquivoColetado, codigo_ibge=None) -> str:
    ano = str(arquivoColetado.ano)
    url_base = "/pdet/microdados/RAIS/"
    url_ano = ano + "/"
    url_final = url_base + url_ano
    ftp = FTP('ftp.mtps.gov.br')
    ftp.login()
    ftp.encoding = "latin-1"
    ftp.cwd(url_final)
    zip_file_remote = arquivoColetado.nome
    tamanho = ftp.size(zip_file_remote)
    arquivoColetado.expected_bytes = tamanho
    arquivoColetado.save()
    dir_zip_file_local = os.path.join(DATA_DIR, ano)
    os.makedirs(dir_zip_file_local, exist_ok=True)
    path_zip_file_local = os.path.join(dir_zip_file_local, zip_file_remote)

    with open(path_zip_file_local, "wb") as f:
        ftp.retrbinary(f"RETR {zip_file_remote}", f.write)

    ftp.quit()

    if os.path.getsize(path_zip_file_local) != tamanho:
        raise RuntimeError(f"Erro no download do arquivo {zip_file_remote} do ano {ano}: tamanho incorreto.")

    arquivoColetado.path_zip = path_zip_file_local
    arquivoColetado.bytes = os.path.getsize(path_zip_file_local)
    arquivoColetado.status = "DOWNLOADED"
    arquivoColetado.save()

    # Extração vai para temp apenas quando for rodada de município(s) específico(s).
    if codigo_ibge is not None:
        dir_extracao = pathlib.Path(dir_zip_file_local) / "temp"
        dir_extracao.mkdir(parents=True, exist_ok=True)
    else:
        dir_extracao = pathlib.Path(dir_zip_file_local)

    with py7zr.SevenZipFile(path_zip_file_local, mode='r') as z:
        nome = z.getnames()[0]
        z.extractall(path=dir_extracao)

    txt_file_local = dir_extracao / nome
    if zip_file_remote.startswith("RAIS_ESTAB_PUB"):
        csv_path = txt_file_local.with_name("RAIS_ESTAB_PUB.csv")
    else:
        csv_path = txt_file_local.with_name("RAIS_VINCULOS_ATIVOS.csv")

    os.rename(txt_file_local, csv_path)
    arquivoColetado.path_extraido = str(csv_path)
    os.remove(arquivoColetado.path_zip)
    arquivoColetado.path_zip = ""
    arquivoColetado.status = "EXTRACTED"
    arquivoColetado.msg = f"{csv_path.name}: {ano}"
    arquivoColetado.save()

    return True


def filtrar_vinc_pub(arquivoColetado: ArquivoColetado, codigo_ibge=None):
    codigos_ibge = _normalizar_ibge(codigo_ibge)

    lista_ibge = codigos_ibge if codigos_ibge is not None else list(
        Municipio.objects.values_list("codigo_ibge", flat=True)
    )

    path_extraido = arquivoColetado.path_extraido
    ano = str(arquivoColetado.ano)

    chunk_size = 100000

    # Saída vai para temp apenas na rodada de município(s) específico(s).
    if codigos_ibge is not None:
        dir_saida = pathlib.Path(path_extraido).parent / "temp"
        dir_saida.mkdir(parents=True, exist_ok=True)
    else:
        dir_saida = pathlib.Path(path_extraido).parent

    saida = dir_saida / f"FILTRADO_RAIS_VINCULOS_ATIVOS_{ano}.csv"
    arquivoColetado.path_filtrado = str(saida)
    arquivoColetado.save()

    if arquivoColetado.ano <= 2022:
        chunks = pd.read_csv(path_extraido, encoding="latin1", chunksize=chunk_size, dtype=str, sep=';')
        cnaes = tuple(cnae for cnae in list(CNAE.objects.values_list("codigo", flat=True)))
    else:
        cnaes = tuple(cnae for cnae in list(CNAE.objects.values_list("codigo", flat=True)))
        chunks = pd.read_csv(path_extraido, encoding="latin1", chunksize=chunk_size, dtype=str)

    colunas_indejesadas = [0, 1, 2, 9, 10, 31]

    linhas_filtradas = 0
    chunk = next(chunks)

    chunk = chunk.drop(chunk.columns[colunas_indejesadas], axis=1)
    chunk[chunk.columns[5]] = chunk[chunk.columns[5]].str.strip()
    mask = chunk[chunk.columns[20]].isin(lista_ibge) & chunk[chunk.columns[5]].str.startswith(cnaes, na=False) & chunk[chunk.columns[17]].str.isdigit() & chunk[chunk.columns[18]].str.isdigit()
    filtrado = chunk[mask]
    filtrado.to_csv(saida, mode="w", index=False, header=True, encoding="utf-8")
    linhas_filtradas += len(filtrado)

    while True:
        try:
            chunk = next(chunks)
            chunk = chunk.drop(chunk.columns[colunas_indejesadas], axis=1)
            chunk[chunk.columns[5]] = chunk[chunk.columns[5]].str.strip()
            mask = chunk[chunk.columns[20]].isin(lista_ibge) & chunk[chunk.columns[5]].str.startswith(cnaes, na=False) & chunk[chunk.columns[17]].str.isdigit() & chunk[chunk.columns[18]].str.isdigit()
            filtrado = chunk[mask]
            filtrado.to_csv(saida, mode="a", index=False, header=False, encoding="utf-8")
            linhas_filtradas += len(filtrado)
        except StopIteration:
            break

    print(f"filtrou {linhas_filtradas} linhas")
    if linhas_filtradas == 0:
        raise RuntimeError(f"Nenhuma linha filtrada para o arquivo {arquivoColetado.nome}.")

    os.remove(arquivoColetado.path_extraido)
    arquivoColetado.path_extraido = ""
    arquivoColetado.linhas_filtradas = linhas_filtradas
    arquivoColetado.status = "FILTERED"
    arquivoColetado.save()

def filtrar_estab_pub(arquivoColetado: ArquivoColetado, codigo_ibge=None):
    codigos_ibge = _normalizar_ibge(codigo_ibge)

    lista_ibge = codigos_ibge if codigos_ibge is not None else list(
        Municipio.objects.values_list("codigo_ibge", flat=True)
    )

    path_extraido = arquivoColetado.path_extraido
    ano = str(arquivoColetado.ano)

    chunk_size = 100000

    if codigos_ibge is not None:
        dir_saida = pathlib.Path(path_extraido).parent / "temp"
        dir_saida.mkdir(parents=True, exist_ok=True)
    else:
        dir_saida = pathlib.Path(path_extraido).parent

    saida = dir_saida / f"FILTRADO_RAIS_ESTABELECIMENTOS_{ano}.csv"
    arquivoColetado.path_filtrado = str(saida)
    arquivoColetado.save()

    cnaes = tuple(cnae for cnae in list(CNAE.objects.values_list("codigo", flat=True)))

    if arquivoColetado.ano <= 2022:
        chunks = pd.read_csv(path_extraido, encoding="latin1", chunksize=chunk_size, dtype=str, sep=';')
    else:
        chunks = pd.read_csv(path_extraido, encoding="latin1", chunksize=chunk_size, dtype=str)

    colunas_indejesadas = [0, 1, 2, 5, 16]

    linhas_filtradas = 0
    chunk = next(chunks)

    chunk = chunk.drop(chunk.columns[colunas_indejesadas], axis=1)
    chunk[chunk.columns[12]] = chunk[chunk.columns[12]].str.strip()
    mask = chunk[chunk.columns[10]].isin(lista_ibge) & chunk[chunk.columns[12]].str.startswith(cnaes, na=False)
    filtrado = chunk[mask]
    filtrado.to_csv(saida, mode="w", index=False, header=True, encoding="utf-8")
    linhas_filtradas += len(filtrado)

    while True:
        try:
            chunk = next(chunks)
            chunk = chunk.drop(chunk.columns[colunas_indejesadas], axis=1)
            chunk[chunk.columns[12]] = chunk[chunk.columns[12]].str.strip()
            mask = chunk[chunk.columns[10]].isin(lista_ibge) & chunk[chunk.columns[12]].str.startswith(cnaes, na=False)
            filtrado = chunk[mask]
            filtrado.to_csv(saida, mode="a", index=False, header=False, encoding="utf-8")
            linhas_filtradas += len(filtrado)
        except StopIteration:
            break

    print(f"filtrou {linhas_filtradas} linhas")
    if linhas_filtradas == 0:
        raise RuntimeError(f"Nenhuma linha filtrada para o arquivo {arquivoColetado.nome}.")

    os.remove(arquivoColetado.path_extraido)
    arquivoColetado.path_extraido = ""
    arquivoColetado.linhas_filtradas = linhas_filtradas
    arquivoColetado.status = "FILTERED"
    arquivoColetado.save()
    
def popular_saldo_mensal(ano, codigo_ibge=None):
    codigos_ibge = _normalizar_ibge(codigo_ibge)

    municipios_codigos = codigos_ibge if codigos_ibge is not None else list(
        Municipio.objects.values_list('codigo_ibge', flat=True)
    )
    cnaes_codigos = CNAE.objects.values_list('codigo', flat=True)
    meses = range(1, 13)

    combinacoes = product(municipios_codigos, cnaes_codigos, meses)

    ultimos_dias = {
        mes: calendar.monthrange(ano, mes)[1]
        for mes in meses
    }

    objetos_rais = []
    for m_id, c_id, mes in combinacoes:
        objetos_rais.append(
            SaldoMensal(
                municipio_id=m_id,
                cnae_id=c_id,
                referencia=date(ano, mes, ultimos_dias[mes])
            )
        )
    if codigo_ibge is not None:
        SaldoMensal.objects.bulk_create(objetos_rais, batch_size=2000, ignore_conflicts=True)
    else:
        SaldoMensal.objects.bulk_create(objetos_rais, batch_size=2000)

def popular_vinculos_ativos(ano, codigo_ibge=None):
    codigos_ibge = _normalizar_ibge(codigo_ibge)

    municipios_codigos = codigos_ibge if codigos_ibge is not None else list(
        Municipio.objects.values_list('codigo_ibge', flat=True)
    )
    cnaes_codigos = CNAE.objects.values_list('codigo', flat=True)
    ultimo_mes = [12]

    combinacoes = product(municipios_codigos, cnaes_codigos, ultimo_mes)

    ultimo_dia = 31

    objetos_rais = []
    for m_id, c_id, mes in combinacoes:
        objetos_rais.append(
            EstoqueAnual(
                municipio_id=m_id,
                cnae_id=c_id,
                referencia=date(ano, mes, ultimo_dia)
            )
        )

    if codigo_ibge is not None:
        EstoqueAnual.objects.bulk_create(objetos_rais, batch_size=2000, ignore_conflicts=True)
    else:
        EstoqueAnual.objects.bulk_create(objetos_rais, batch_size=2000)

def carregar_vinc_pub(arquivoColetado: ArquivoColetado, codigo_ibge=None):
    ano = arquivoColetado.ano
    popular_saldo_mensal(ano, codigo_ibge=codigo_ibge)

    meses = range(1, 13)
    ultimos_dias = {
        mes: calendar.monthrange(ano, mes)[1]
        for mes in meses
    }

    path_filtrado = arquivoColetado.path_filtrado
    df = pd.read_csv(path_filtrado, encoding="utf-8", dtype=str)

    for idx, row in df.iterrows():
        municipio_ibge = row[df.columns[20]]
        cnae_codigo = row[df.columns[5]][0:5]
        mes_admissao = int(row[df.columns[17]])
        mes_desligamento = int(row[df.columns[18]])

        # Otimização: remove os 2 SELECTs (Municipio.objects.get / CNAE.objects.get)
        # por linha -- filter().update() aceita FK por id diretamente.
        if mes_admissao != 0:
            data_referencia = date(int(ano), int(mes_admissao), ultimos_dias[mes_admissao])
            try:
                SaldoMensal.objects.filter(
                    municipio_id=municipio_ibge,
                    cnae_id=cnae_codigo,
                    referencia=data_referencia
                ).update(saldo=F("saldo") + 1)
            except Exception:
                print("Algo deu errado")

        if mes_desligamento != 0:
            data_referencia = date(int(ano), int(mes_desligamento), ultimos_dias[mes_desligamento])
            try:
                SaldoMensal.objects.filter(
                    municipio_id=municipio_ibge,
                    cnae_id=cnae_codigo,
                    referencia=data_referencia
                ).update(saldo=F("saldo") - 1)
            except Exception as e:
                print(cnae_codigo)
                print(e)
                raise e

    arquivoColetado.status = "LOADED"
    arquivoColetado.save()
    print("carregou")

def carregar_estab_pub(arquivoColetado: ArquivoColetado, codigo_ibge=None):
    ano = arquivoColetado.ano
    popular_vinculos_ativos(ano, codigo_ibge=codigo_ibge)

    mes = 12
    ultimo_dia = 31
    data_referencia = date(ano, mes, ultimo_dia)
    path_filtrado = arquivoColetado.path_filtrado

    df = pd.read_csv(path_filtrado, encoding="utf-8", dtype=str)

    for idx, row in df.iterrows():
        municipio_ibge = row[df.columns[10]]
        cnae_codigo = row[df.columns[12]][0:5]
        qtd_vinculos_ativos = int(row[df.columns[3]])

        # Mesma otimização: sem gets prévios, FK direto por id.
        EstoqueAnual.objects.filter(
            municipio_id=municipio_ibge,
            cnae_id=cnae_codigo,
            referencia=data_referencia
        ).update(estoque=F("estoque") + qtd_vinculos_ativos)

    arquivoColetado.status = "LOADED"
    arquivoColetado.save()
    print("carregou")


# Este nome aqui esta ruim. A função não carrega os saldos mensais, ela atualiza os estoques mensais com base nos saldos mensais e nos estoques anuais. Talvez seja melhor renomear para "atualizar_estoques_mensais_com_saldos" ou algo do tipo.
#seria bom declarar a variavel qtd antes do if, para evitar problemas de escopo e melhorar a legibilidade do código.
def carregar_saldos_mensais(year: int, codigo_ibge=None):
    """
    Atualiza EstoqueMensal a partir de EstoqueAnual (ano anterior) + SaldoMensal (ano atual).

    Fluxo normal (codigo_ibge=None): EstoqueMensal já existe (pipeline anual
    padrão) -> get + save, igual ao comportamento original.

    Fluxo cidade nova (codigo_ibge informado): EstoqueMensal do ano/mês pode
    ainda não existir para esse município -> update_or_create.
    """
    codigos_ibge = _normalizar_ibge(codigo_ibge)

    ano_anterior = year - 1
    estoques_anuais = EstoqueAnual.objects.filter(referencia__year=ano_anterior)
    saldos_mensais = SaldoMensal.objects.filter(referencia__year=year)

    if codigos_ibge is not None:
        estoques_anuais = estoques_anuais.filter(municipio_id__in=codigos_ibge)
        saldos_mensais = saldos_mensais.filter(municipio_id__in=codigos_ibge)

    #Sugestão (não ativada): avisar quando não há base para nivelar.
    if not estoques_anuais.exists():
        raise  RuntimeError(f"Sem EstoqueAnual em {ano_anterior} para os municípios informados; nada a nivelar em {year}.")

    qtd = None
    for estoque in estoques_anuais:
        for mes in range(1, 13):
            
            data = gerar_ultimo_dia(year, mes)
            if mes == 1:
                saldo = saldos_mensais.get(municipio=estoque.municipio, cnae=estoque.cnae, referencia=data)
                qtd = estoque.estoque + saldo.saldo
            elif mes == 12:
                estoque_desse_ano = EstoqueAnual.objects.get(municipio=estoque.municipio, cnae=estoque.cnae, referencia=data)
                qtd = estoque_desse_ano.estoque
            else:
                saldo = saldos_mensais.get(municipio=estoque.municipio, cnae=estoque.cnae, referencia=data)
                qtd += saldo.saldo

            if codigos_ibge is not None:
                EstoqueMensal.objects.update_or_create(
                    municipio=estoque.municipio,
                    cnae=estoque.cnae,
                    referencia=data,
                    defaults={"estoque": qtd},
                )
            else:
                estq = EstoqueMensal.objects.get(municipio=estoque.municipio, cnae=estoque.cnae, referencia=data)
                estq.estoque = qtd
                estq.save(update_fields=["estoque"])