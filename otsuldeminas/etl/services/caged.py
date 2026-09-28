from ftplib import FTP
from django.conf import settings
from django.db.models import F
from etl.models import ArquivoColetado
from etl.utils import registrar_log
from cadastros.models import CNAE, Municipio
from caged.models import SaldoMensalCaged
from rais.models import EstoqueAnual, EstoqueMensal
import os
import py7zr
import pathlib
import pandas as pd
import calendar
from datetime import date
from itertools import product

BASE_DIR = pathlib.Path(settings.BASE_DIR)
DATA_DIR = BASE_DIR / "data" / "caged"

def _normalizar_ibge(codigo_ibge):
    """Normaliza o argumento opcional de município(s) para uma lista de strings
    (ou None, caso não tenha sido informado). Mantém idempotência caso já
    receba uma lista/tupla/set."""
    if codigo_ibge is None:
        return None
    if isinstance(codigo_ibge, (list, tuple, set)):
        return [str(c) for c in codigo_ibge]
    return [str(codigo_ibge)]

def gerar_ultimo_dia(ano, mes):
    _, ultimo_dia = calendar.monthrange(ano, mes)
    return date(ano,mes,ultimo_dia)

def baixar_caged(arquivoColetado: ArquivoColetado, codigo_ibge=None):
    ano = str(arquivoColetado.ano)
    mes = str(arquivoColetado.mes)
    if len(mes) == 1:
        mes = "0" + mes

    ano_mes = ano + mes

    url_base = "/pdet/microdados/NOVO CAGED/"
    url_ano = ano + "/"
    url_final = url_base + url_ano + ano_mes + "/"

    ftp = FTP("ftp.mtps.gov.br")
    ftp.login()
    ftp.encoding = "latin-1"
    ftp.cwd(url_final)

    zip_file_remote = arquivoColetado.nome + ano_mes + ".7z"
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
    if zip_file_remote.startswith("CAGEDMOV"):
        csv_path = txt_file_local.with_name(f"MOV_{ano_mes}.csv")
    elif zip_file_remote.startswith("CAGEDFOR"):
        csv_path = txt_file_local.with_name(f"FOR_{ano_mes}.csv")
    else:
        csv_path = txt_file_local.with_name(f"EXC_{ano_mes}.csv")
    os.rename(txt_file_local, csv_path)
    arquivoColetado.path_extraido = str(csv_path)
    os.remove(arquivoColetado.path_zip)
    arquivoColetado.path_zip = ""
    arquivoColetado.status = "EXTRACTED"
    arquivoColetado.msg = f"{csv_path.name}: {ano}"
    arquivoColetado.save()

    return True

def filtrar_caged(arquivoColetado: ArquivoColetado, codigo_ibge=None):
    codigos_ibge = _normalizar_ibge(codigo_ibge)

    lista_ibge = codigos_ibge if codigos_ibge is not None else list(
        Municipio.objects.values_list("codigo_ibge", flat=True)
    )
    cnaes = list(CNAE.objects.values_list("codigo", flat=True))

    linhas_filtradas = 0
    path_extraido = arquivoColetado.path_extraido
    nome = pathlib.Path(path_extraido).name

    chunk_size = 100000

    # Arquivo filtrado só vai para temp quando codigo_ibge foi informado;
    # caso contrário, fica no mesmo diretório do arquivo extraído (fluxo normal).
    if codigos_ibge is not None:
        dir_saida = pathlib.Path(path_extraido).parent / "temp"
        dir_saida.mkdir(parents=True, exist_ok=True)
    else:
        dir_saida = pathlib.Path(path_extraido).parent

    saida = dir_saida / f"FILTRADO_{nome}"
    arquivoColetado.path_filtrado = str(saida)
    arquivoColetado.save()

    chunks = pd.read_csv(path_extraido, sep=";", dtype=str, chunksize=chunk_size, encoding="latin-1")

    chunk = next(chunks)

    mask = chunk[chunk.columns[3]].isin(lista_ibge) & chunk[chunk.columns[5]].str[0:5].isin(cnaes)
    filtrado = chunk[mask]
    filtrado.to_csv(saida, mode="w", index=False, header=True, encoding="latin-1")
    linhas_filtradas += len(filtrado)

    while True:
        try:
            chunk = next(chunks)
            mask = chunk[chunk.columns[3]].isin(lista_ibge) & chunk[chunk.columns[5]].str[0:5].isin(cnaes)
            filtrado = chunk[mask]
            filtrado.to_csv(saida, mode="a", index=False, header=False, encoding="latin-1")
            linhas_filtradas += len(filtrado)
        except StopIteration:
            break

    print(f"filtrou {linhas_filtradas} linhas")
    if linhas_filtradas == 0 and arquivoColetado.nome.startswith("CAGEDMOV"):
        raise RuntimeError(f"Nenhuma linha filtrada para o arquivo {nome}.")

    os.remove(arquivoColetado.path_extraido)
    arquivoColetado.path_extraido = ""
    arquivoColetado.linhas_filtradas = linhas_filtradas
    arquivoColetado.status = "FILTERED"
    arquivoColetado.save()

def popular_caged(ano, mes, codigo_ibge=None):
    codigos_ibge = _normalizar_ibge(codigo_ibge)

    municipios_codigos = codigos_ibge if codigos_ibge is not None else list(
        Municipio.objects.values_list('codigo_ibge', flat=True)
    )
    cnaes_codigos = CNAE.objects.values_list('codigo', flat=True)

    combinacoes = product(municipios_codigos, cnaes_codigos, [mes])

    ultimo_dia = calendar.monthrange(ano, mes)[1]
    referencia = date(ano, mes, ultimo_dia)

    caged_objs = []
    for municipio_codigo, cnae_codigo, mes in combinacoes:
        caged_objs.append(SaldoMensalCaged(
            municipio_id=municipio_codigo,
            cnae_id=cnae_codigo,
            referencia=referencia,
        ))

    # ignore_conflicts evita erro/duplicidade quando popular_caged é chamado
    # com um subconjunto de municípios cujas combinações já existam.
    if codigo_ibge is not None:    
        SaldoMensalCaged.objects.bulk_create(caged_objs, batch_size=2000, ignore_conflicts=True)
    else:
        SaldoMensalCaged.objects.bulk_create(caged_objs, batch_size=2000)

def carregar_caged_mov(arquivoColetado: ArquivoColetado, codigo_ibge=None):
    
    ano = arquivoColetado.ano
    mes = arquivoColetado.mes
    popular_caged(ano, mes, codigo_ibge=codigo_ibge)
    
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    refencia = date(ano, mes, ultimo_dia)
    path_filtrado = arquivoColetado.path_filtrado
    
    df = pd.read_csv(path_filtrado, dtype=str)
    
    for _, row in df.iterrows():
        municipio_codigo = row.iloc[3]
        cnae_codigo = row.iloc[5][0:5]
        movimentacao = int(row.iloc[6])
        
        SaldoMensalCaged.objects.filter(
            municipio_id=municipio_codigo,
            cnae_id=cnae_codigo,
            referencia=refencia
        ).update(saldo_caged=F("saldo_caged") + movimentacao)

    
    arquivoColetado.status = "LOADED"
    arquivoColetado.save()
    print("carregou")
    
def carregar_caged_for(arquivoColetado: ArquivoColetado, codigo_ibge=None):
    
    path_filtrado = arquivoColetado.path_filtrado
    df = pd.read_csv(path_filtrado, dtype=str)
    
    for _, row in df.iterrows():
        
        ano = int(row.iloc[0][0:4])
        mes = int(row.iloc[0][4:6])
        municipio_codigo = row.iloc[3]
        cnae_codigo = row.iloc[5][0:5]
        movimentacao = int(row.iloc[6])
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        referencia = date(ano, mes, ultimo_dia)
        
        SaldoMensalCaged.objects.filter(
            municipio_id=municipio_codigo,
            cnae_id=cnae_codigo,
            referencia=referencia,
        ).update(saldo_caged=F("saldo_caged") + movimentacao)
        
    arquivoColetado.status = "LOADED"
    arquivoColetado.save()
    print("carregou")
        
def carregar_caged_exc(arquivoColetado: ArquivoColetado, codigo_ibge=None):
    
    path_filtrado = arquivoColetado.path_filtrado
    df = pd.read_csv(path_filtrado, dtype=str)
    
    for _, row in df.iterrows():
        
        ano = int(row.iloc[0][0:4])
        mes = int(row.iloc[0][4:6])
        municipio_codigo = row.iloc[3]
        cnae_codigo = row.iloc[5][0:5]
        movimentacao = -1 * int(row.iloc[6])
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        referencia = date(ano, mes, ultimo_dia)
        

        SaldoMensalCaged.objects.filter(
            municipio_id=municipio_codigo,
            cnae_id=cnae_codigo,
            referencia=referencia,
        ).update(saldo_caged=F("saldo_caged") + movimentacao)

    arquivoColetado.status = "LOADED"
    arquivoColetado.save()
    print("carregou")

# Este nome também está ruim. A função não carrega os saldos mensais, ela atualiza os estoques mensais com base nos saldos mensais e nos estoques anuais. Talvez seja melhor renomear para "atualizar_estoques_mensais_com_saldos" ou algo do tipo.
def carregar_saldos_mensais_temporarios(year: int, month: int, codigo_ibge=None):
    codigos_ibge = _normalizar_ibge(codigo_ibge)

    #ano_estoque_anual_mais_recente = EstoqueAnual.objects.order_by("-referencia").first().referencia.year
    mes_atual = gerar_ultimo_dia(year, month)
    if month == 1:
        mes_anterior = date(year - 1, 12, 31)
    else:
        mes_anterior = gerar_ultimo_dia(year, month - 1)

    if EstoqueMensal.objects.filter(referencia=mes_anterior).exists():
        estoques_mes_anterior = EstoqueMensal.objects.filter(referencia=mes_anterior)
        if codigos_ibge is not None:
            estoques_mes_anterior = estoques_mes_anterior.filter(municipio_id__in=codigos_ibge)

        saldos_mensais_caged = SaldoMensalCaged.objects.filter(referencia=mes_atual)
        if codigos_ibge is not None:
            saldos_mensais_caged = saldos_mensais_caged.filter(municipio_id__in=codigos_ibge)

        for estoque in estoques_mes_anterior:
            saldo = saldos_mensais_caged.get(municipio=estoque.municipio, cnae=estoque.cnae)
            qtd = estoque.estoque + saldo.saldo_caged
            EstoqueMensal.objects.create(municipio=estoque.municipio, cnae=estoque.cnae, referencia=mes_atual, estoque=qtd)
    else:
        raise RuntimeError("O ano passado eh menor do que o rais atual ou nao ha estoque para o mes anterior") 