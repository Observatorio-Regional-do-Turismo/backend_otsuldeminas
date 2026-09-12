import requests
import os
import charset_normalizer
import shutil
import csv
from datetime import date, datetime
import pathlib
from pathlib import Path
from django.conf import settings
from etl.models import ArquivoColetado
from cadastros.models import CNAE, Municipio
from receita_federal.models import Estabelecimento
from etl.consts import SELECT_ORDER, IDX
from bs4 import BeautifulSoup 
from requests.exceptions import HTTPError

BASE_DIR = pathlib.Path(settings.BASE_DIR)
DATA_DIR = BASE_DIR / "data" / "receita_federal"
url_casa_dos_dados = "https://dados-abertos-rf-cnpj.casadosdados.com.br/arquivos/"

def _lista_codigo_municipios_rf() -> set[str]:
    # cache leve por processo
    if not hasattr(_lista_codigo_municipios_rf, "_cache"):
        _lista_codigo_municipios_rf._cache = set(Municipio.objects.values_list("codigo_receita_federal", flat=True))
    return _lista_codigo_municipios_rf._cache

def _lista_codigos_cnae() -> set[str]:
    if not hasattr(_lista_codigos_cnae, "_cache"):
        _lista_codigos_cnae._cache = set(CNAE.objects.values_list("codigo", flat=True))
    return _lista_codigos_cnae._cache

def _lista_cnpj_completo_estabelecimentos() -> set[str]:
    if not hasattr(_lista_cnpj_completo_estabelecimentos, "_cache"):
        _lista_cnpj_completo_estabelecimentos._cache = set(Estabelecimento.objects.values_list("cnpj_completo", flat=True))
    return _lista_cnpj_completo_estabelecimentos._cache

def baixar_arquivo_rf( # baixar receita federal
    nome_arquivo_servidor: str,
    nome_arquivo_local: str,
    ano_mes: str,
    arquivo_coletado: ArquivoColetado,
) -> ArquivoColetado:
    
    response = requests.get(url_casa_dos_dados)
    soup = BeautifulSoup(response.text, 'html.parser')
    print(f"Procurando pastas em: {url_casa_dos_dados}\n")
    url_pasta = None
    # Varre todos os links da página
    for link in soup.find_all('a'):
      href = link.get('href')
   
      # Verifica se o link existe e começa com o padrão desejado
      if href and href.startswith(ano_mes):
          print(f"Pasta encontrada: {href}")
   
          # Se você quiser montar a URL completa para usar depois:
          url_pasta = url_casa_dos_dados + href
          print(f"URL para acesso: {url_pasta}")
    
    if not url_pasta:
        response = requests.Response()
        response.status_code = 404
        raise HTTPError(f"Pasta para ano_mes {ano_mes} não encontrada em {url_casa_dos_dados}", response=response)
    
    url = os.path.join(url_pasta, nome_arquivo_servidor) # https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/2025-07/Estabelecimentos0.zip
    
    path_zip = os.path.join(DATA_DIR, ano_mes)
    os.makedirs(path_zip, exist_ok=True)
    path_zip = os.path.join(path_zip, nome_arquivo_local)
       
    re = requests.head(url)
    re.raise_for_status() 
    file_size = int(re.headers.get("Content-Length", 0))
    arquivo_coletado.expected_bytes = file_size
    
    if os.path.exists(path_zip):
        resume_byte_pos = os.path.getsize(path_zip)
        headers = {"Range": f"bytes={resume_byte_pos}-"}
        with requests.get(url, headers=headers, stream=True) as r:
            if r.status_code in (200, 206):
                mode = "ab" if resume_byte_pos > 0 else "wb"
                with open(path_zip, mode) as f:
                    for chunk in r.iter_content(chunk_size=128):
                        f.write(chunk)
    else:
        with requests.get(url, stream=True) as r:
            print(r.status_code)
            if r.status_code == 200:
                with open(path_zip, "wb") as f:
                    for chunk in r.iter_content(chunk_size=128):
                        f.write(chunk)
    
    if os.path.getsize(path_zip) == file_size:
        print("True")
        arquivo_coletado.bytes = file_size
        arquivo_coletado.status = "DOWNLOADED"
        arquivo_coletado.path_zip = path_zip
        arquivo_coletado.save()
        return arquivo_coletado
    else:
        os.remove(path_zip)
        raise RuntimeError("Download incompleto ou corrompido")

def extrair_arquivo_rf(
    arquivo_coletado: ArquivoColetado, 
) -> pathlib.Path:
    import zipfile

    extract_path = Path(arquivo_coletado.path_zip).with_suffix(".csv")  # remove .zip
    #os.makedirs(extract_path, exist_ok=True)

    with zipfile.ZipFile(arquivo_coletado.path_zip, 'r') as zip_ref:
        #zip_ref.extractall(extract_path)       
        target = None
        for info in zip_ref.infolist():
            name = info.filename
            if any(tipo in name for tipo in ['ESTABELE', 'SOCIO']):
                target = name
                break
        if not target:
            raise RuntimeError("Arquivo útil não encontrado dentro do zip")

        with zip_ref.open(target) as zin, extract_path.open("wb") as fout:
            shutil.copyfileobj(zin, fout)


    arquivo_coletado.path_extraido = str(extract_path)
    arquivo_coletado.status = "EXTRACTED"
    os.remove(arquivo_coletado.path_zip)
    arquivo_coletado.path_zip = ""
    arquivo_coletado.save()
    return arquivo_coletado    

def filtrar_arquivo_rf(
    arquivo_coletado: ArquivoColetado,
) -> ArquivoColetado:
    extracted_path = arquivo_coletado.path_extraido
    
    if arquivo_coletado.nome.startswith("Estabelecimentos"):
        lista_codigo_municipios_rf = _lista_codigo_municipios_rf()
        lista_codigos_cnae = _lista_codigos_cnae()
        col_idx = IDX["Estabelecimentos"] 
        filtered_path = Path(extracted_path).with_name(f"filtrado_{Path(extracted_path).name}")
        total_out = 0
        #detectar encoding do arquivo extraído
        with open(extracted_path, "rb") as rawdata:
            result = charset_normalizer.detect(rawdata.read(1000000))
            encoding = result['encoding'] or "latin-1"
            if encoding.lower() == "ascii":
                encoding = "latin-1"
            print(encoding)

        with open(extracted_path, "r", encoding=encoding, newline="") as fin, filtered_path.open("w", encoding="utf-8", newline="") as fout:
            reader = csv.reader(fin, delimiter=";")
            writer = csv.writer(fout, delimiter=";")
            # header do bronze filtrado
            writer.writerow(SELECT_ORDER[0])
            for row in reader:
                # alguns dumps vêm SEM header; se detectar header, pule
                if row and row[0].upper().startswith("CNPJ"):
                    continue
                try:
                    mun = int(row[col_idx["codigo_municipio_rf"]])
                    cnae = str(row[col_idx["cnae_fiscal_principal"]])[:5]
                    #if total_out % 1000000 == 0:
                        #print(cnae)
                except Exception:
                    continue
                if mun in lista_codigo_municipios_rf and cnae in lista_codigos_cnae:
                    #print("Esta")
#                    municipio = Municipio.objects.get(codigo_receita_federal = mun)
                    out_row = [
                        (str(row[0]) + str(row[1]) + str(row[2])) if col == "cnpj_completo" 
                        else row[col_idx[col]]
                        for col in SELECT_ORDER[0]
                    ]

                    #out_row = [row[col_idx[col]] if col != "mes" else mes for col in sel]

                    writer.writerow(out_row)
                    total_out += 1
        
        if total_out == 0:
            raise RuntimeError(f"Nenhuma linha filtrada para o arquivo {arquivo_coletado.nome}.")

        arquivo_coletado.path_filtrado = str(filtered_path)
        arquivo_coletado.linhas_filtradas = total_out
        arquivo_coletado.status = "FILTERED"
        os.remove(arquivo_coletado.path_extraido)
        arquivo_coletado.path_extraido = ""
        arquivo_coletado.save()
        return arquivo_coletado

def carregar_arquivo_rf(
    arquivo_coletado: ArquivoColetado,
) -> ArquivoColetado:
    path_filtrado = arquivo_coletado.path_filtrado
    if arquivo_coletado.nome.startswith("Estabelecimentos"):
        counter_loaded = 0
        with open(path_filtrado, "r", encoding="utf-8", newline="") as fin:
            reader = csv.reader(fin, delimiter=";")
            header = next(reader)  # pular header
            for row in reader:
                try:
                    data_situacao_cadastral = datetime.strptime(row[7], "%Y%m%d").date().isoformat() if len(str(row[7])) == 8 else None
                    data_inicio_atividade = datetime.strptime(row[11], "%Y%m%d").date().isoformat() if len(str(row[11])) == 8 else None
                    data_situacao_especial = datetime.strptime(row[30], "%Y%m%d").date().isoformat() if len(str(row[30])) == 8 else None
                    Estabelecimento.objects.update_or_create(
                        cnpj_completo = str(row[0]),
                        defaults = {
                            "cnpj_basico": str(row[1]),
                            "cnpj_ordem": str(row[2]),
                            "cnpj_dv": str(row[3]),
                            "identidade_matriz_ou_filial": int(row[4]),
                            "nome_fantasia": str(row[5]),
                            "situacao_cadastral": str(row[6]) if len(str(row[6])) <= 2 else "",
                            "data_situacao_cadastral": data_situacao_cadastral,
                            "motivo_situacao_cadastral": int(row[8]) if row[8] else None,
                            "nome_cidade_exterior": str(row[9]),
                            "codigo_pais": str(row[10]) if len(str(row[10])) <= 10 else "",
                            "data_inicio_atividade": data_inicio_atividade,
                            "classe_cnae_id": str(row[12])[:5],
                            "cnae_fiscal_principal": str(row[12]),
                            "cnae_fiscal_secundaria": str(row[13]),
                            "tipo_logradouro": str(row[14]) if len(str(row[14])) <= 30 else "",
                            "logradouro": str(row[15]),
                            "numero": str(row[16]) if len(str(row[16])) <=10 else "",
                            "complemento": str(row[17]),
                            "bairro": str(row[18]),
                            "cep": str(row[19]) if len(str(row[19])) == 8 else "",
                            "uf": str(row[20]) if len(str(row[20])) ==2 else "",
                            "codigo_municipio_rf_id": str(row[21]),
                            "dd1": str(row[22]) if len(str(row[22])) <= 3 else "",
                            "telefone1": str(row[23]) if len(str(row[23])) <= 15 else "",
                            "ddd2": str(row[24]) if len(str(row[24])) <= 3 else "",
                            "telefone2": str(row[25]) if len(str(row[25])) <= 15 else "",
                            "dddfax": str(row[26]) if len(str(row[26])) <= 3 else "",
                            "fax": str(row[27]) if len(str(row[27])) <= 15 else "",
                            "email": str(row[28]),
                            "situacao_especial": str(row[29]),
                            "data_situacao_especial": data_situacao_especial,
                            "data_atualizacao": datetime.now(),
                        }
                    )
                    counter_loaded += 1
                
                except Exception as e:
                    arquivo_coletado.msg += f"\nErro ao carregar estabelecimento CNPJ {row[0]}: {e}"
                    arquivo_coletado.save(update_fields=["msg"])
                    continue
        print(f"Total carregado: {counter_loaded}")      
        arquivo_coletado.status = "LOADED"
        # arquivo_coletado.msg = f"{total_loaded} estabelecimentos carregados."
        arquivo_coletado.save(update_fields=["status", "msg"])
        return arquivo_coletado
    
