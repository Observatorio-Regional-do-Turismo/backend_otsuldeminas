from celery import shared_task, chain, chord
from celery.exceptions import SoftTimeLimitExceeded
from requests.exceptions import Timeout, ConnectionError, RequestException, HTTPError
from datetime import date
from .services.receita_federal import baixar_arquivo_rf, extrair_arquivo_rf, filtrar_arquivo_rf, carregar_arquivo_rf
from .services.rais import baixar_rais, filtrar_vinc_pub, carregar_vinc_pub, filtrar_estab_pub, carregar_estab_pub, carregar_saldos_mensais
from .services.caged import baixar_caged, filtrar_caged, carregar_caged_mov, carregar_caged_for, carregar_caged_exc, carregar_saldos_mensais_temporarios
from .models import ArquivoColetado
from .utils import registrar_log
from caged.models import SaldoMensalCaged
from datetime import date
from dateutil.relativedelta import relativedelta
from django.db.models import Max
from website_backend.models import Cidade
from .services.ibge import collect_city_indicators

@shared_task(
    bind=True,
    soft_time_limit= 30 * 60,
    autoretry_for =(Timeout, ConnectionError, SoftTimeLimitExceeded),
    retry_backoff=True,   # 1s, 2s, 4s, 8s...
    retry_jitter=True,    # adiciona aleatoriedade nesses tempos
    retry_kwargs={"max_retries": 10},
)
def task_baixar_arquivo_rf(
    self,
    nome_arquivo_servidor : str,
    ano_mes: str,
    ):
            
    nome_arquivo_local = (
        nome_arquivo_servidor[: len(nome_arquivo_servidor) - 4] 
        + "_" 
        + ano_mes 
        + ".zip"
    )
    arquivo_coletado, _ = ArquivoColetado.objects.get_or_create(
        nome=nome_arquivo_local,
        ano=int(ano_mes[:4]),
        mes=int(ano_mes[5:7])
    )
    arquivo_coletado.status = "PENDING"
    arquivo_coletado.save()
    try:
        arquivo_coletado = baixar_arquivo_rf(
                                nome_arquivo_servidor=nome_arquivo_servidor,
                                nome_arquivo_local=nome_arquivo_local,
                                ano_mes=ano_mes,
                                arquivo_coletado=arquivo_coletado
                            )
        registrar_log(
            operacao="DOWNLOAD",
            arquivo=nome_arquivo_local,
            data_referencia=ano_mes,
            sucesso=True,
        )
        return arquivo_coletado.id
        
    except (Timeout, ConnectionError, SoftTimeLimitExceeded):
        # Essas exceções são tratadas pelo autoretry_for automaticamente
        registrar_log(
            operacao="DOWNLOAD",
            arquivo=nome_arquivo_local,
            data_referencia=ano_mes,
            sucesso=False,
            erro="Timeout, ConnectionError ou SoftTimeLimitExceeded",
        )
        raise

    except HTTPError as e:
        if e.response.status_code == 404: #a rquivo não encontrado
            print("Ih rapaiz")
            registrar_log(
                operacao="DOWNLOAD",
                arquivo=nome_arquivo_local,
                data_referencia=ano_mes,
                sucesso=False,
                erro="Arquivo não encontrado",
            )
            raise self.retry(
            countdown= 7 * 24 * 60 * 60,  # tenta de novo em uma semana
            max_retries=4,           # tenta por um mes
        )
        raise e  # re-raise para outras exceções HTTP
    except RuntimeError as e:
        print(e)
        registrar_log(
            operacao="DOWNLOAD",
            arquivo=nome_arquivo_local,
            data_referencia=ano_mes,
            sucesso=False,
            erro=str(e),
        )
        raise self.retry(
            countdown= 5 * 60,  # tenta de novo em 10 minutos
            max_retries=5,           
        )
    except Exception as e:
        print(e)
        registrar_log(
            operacao="DOWNLOAD",
            arquivo=nome_arquivo_local,
            data_referencia=ano_mes,
            sucesso=False,
            erro=str(e),
        )
        raise self.retry(
            countdown= 10 * 60,  # tenta de novo em 10 minutos
            max_retries=5,           
        )
        
@shared_task(
    bind=True,
)
def task_extrair_arquivo_rf(
    self,
    id_arquivoColetado : int,
):
    arquivoColetado = ArquivoColetado.objects.get(id=id_arquivoColetado)
    try:
        arquivoColetado = extrair_arquivo_rf(arquivoColetado)
        registrar_log(
            operacao="EXTRACAO",
            arquivo=arquivoColetado.nome,
            data_referencia=f"{arquivoColetado.ano}-{arquivoColetado.mes:02d}",
            sucesso=True,
        )
        return arquivoColetado.id
    except RuntimeError as e:
        print(e)
        registrar_log(
            operacao="EXTRACAO",
            arquivo=arquivoColetado.nome,
            data_referencia=f"{arquivoColetado.ano}-{arquivoColetado.mes:02d}",
            sucesso=False,
            erro=str(e),
        )
        arquivoColetado.status = "ERROR"
        arquivoColetado.msg = str(e)
        arquivoColetado.save()
        raise

@shared_task(
    bind=True,
)
def task_filtrar_dados_rf(
    self,
    id_arquivoColetado : int,
):
    arquivoColetado = ArquivoColetado.objects.get(id=id_arquivoColetado)
    try:
        arquivoColetado = filtrar_arquivo_rf(arquivoColetado)
        registrar_log(
            operacao="FILTRO",
            arquivo=arquivoColetado.nome,
            data_referencia=f"{arquivoColetado.ano}-{arquivoColetado.mes:02d}",
            sucesso=True,
        )
        return arquivoColetado.id
    except RuntimeError as e:
        print(e)
        registrar_log(
            operacao="FILTRAGEM",
            arquivo=arquivoColetado.nome,
            data_referencia=f"{arquivoColetado.ano}-{arquivoColetado.mes:02d}",
            sucesso=False,
            erro=str(e),
        )
        arquivoColetado.status = "ERROR"
        arquivoColetado.msg += "\n"
        arquivoColetado.msg += str(e)
        arquivoColetado.save()
        raise
    except Exception as e:
        print(e)
        registrar_log(
            operacao="FILTRAGEM",
            arquivo=arquivoColetado.nome,
            data_referencia=f"{arquivoColetado.ano}-{arquivoColetado.mes:02d}",
            sucesso=False,
            erro=str(e),
        )
        arquivoColetado.status = "ERROR"
        arquivoColetado.msg += "\n"
        arquivoColetado.msg += str(e)
        arquivoColetado.save()
        raise

@shared_task(
    bind=True,
)
def task_carregar_dados_rf(
    self,
    id_arquivoColetado : int,
):
    arquivoColetado = ArquivoColetado.objects.get(id=id_arquivoColetado)
    try:
        arquivoColetado = carregar_arquivo_rf(arquivoColetado)
        registrar_log(
            operacao="CARGA",
            arquivo=arquivoColetado.nome,
            data_referencia=f"{arquivoColetado.ano}-{arquivoColetado.mes:02d}",
            sucesso=True,
        )
        return arquivoColetado.id
    except RuntimeError as e:
        print(e)
        registrar_log(
            operacao="CARGA",
            arquivo=arquivoColetado.nome,
            data_referencia=f"{arquivoColetado.ano}-{arquivoColetado.mes:02d}",
            sucesso=False,
            erro=str(e),
        )
        arquivoColetado.status = "ERROR"
        arquivoColetado.msg += "\n"
        arquivoColetado.msg += str(e)
        arquivoColetado.save()
        raise
    
@shared_task(
    bind=True,
)
def task_coletar_arquivo_rf(
    self,
    nome_arquivo_servidor : str,
    **kwargs,
    ):
    
    if "data" in kwargs:
        ano_mes = kwargs["data"]
    else:
        ano_mes = str(date.today())[0:7] # '2025-07'
    
    # id_arquivo_coletado = task_baixar_arquivo_rf(
    #                         nome_arquivo_servidor=nome_arquivo_servidor,
    #                         ano_mes=ano_mes,
    #                     )
    
    ch = chain(
        task_baixar_arquivo_rf.s(nome_arquivo_servidor=nome_arquivo_servidor, ano_mes=ano_mes),
        task_extrair_arquivo_rf.s(),
        task_filtrar_dados_rf.s(),
        task_carregar_dados_rf.s(),
    )
    async_result = ch.apply_async()
    print(f"Coleta do arquivo {nome_arquivo_servidor} disparada: {async_result.id}")
    
    return async_result.id
    
    
@shared_task
def task_teste(**kwargs):
    if "opa" in kwargs:
        return f"Teste OK! opa={kwargs['opa']}"
    return "Nenhum parâmetro recebido."


@shared_task(
    bind=True,
    autoretry_for=(Timeout, ConnectionError),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def task_coletar_indicadores_ibge(self, cidade_id: int | None = None):
    """Collect IBGE indicators for one city or every registered city."""
    if cidade_id is not None:
        cidade = Cidade.objects.get(pk=cidade_id)
        collect_city_indicators(cidade)
        return cidade_id

    for cidade in Cidade.objects.exclude(ibge_code__isnull=True).exclude(ibge_code=""):
        collect_city_indicators(cidade)


@shared_task(
    bind=True,
)
def task_baixar_rais(
    self,
    ano: str,
    nome_arquivo_servidor : str,
    ):
           
    arquivo_coletado, _ = ArquivoColetado.objects.get_or_create(
        nome=nome_arquivo_servidor,
        ano=int(ano),
    )
    arquivo_coletado.status = "PENDING"
    arquivo_coletado.save()
    try:
        baixar_rais(arquivoColetado=arquivo_coletado)      
    except Exception as e:
        arquivo_coletado.status = "FAILED"
        arquivo_coletado.msg = str(e)
        arquivo_coletado.save()
        raise   
    
    return arquivo_coletado.id 

# @shared_task(
#     bind=True,
# )
# def task_filtrar_vinc_pub(
#     self,
#     id_arquivoColetado : int,
# ):
#     arquivoColetado = ArquivoColetado.objects.get(id=id_arquivoColetado)
#     try:
#         filtrar_vinc_pub(arquivoColetado)
#         return arquivoColetado.id
#     except Exception as e:
#         print(e)
#         arquivoColetado.status = "ERROR"
#         arquivoColetado.msg = str(e)
#         arquivoColetado.save()
#         raise

# @shared_task(
#     bind=True,
# )
# def task_filtrar_estab_pub(
#     self,
#     id_arquivoColetado : int,
# ):
#     arquivoColetado = ArquivoColetado.objects.get(id=id_arquivoColetado)
#     try:
#         filtrar_estab_pub(arquivoColetado)
#         return arquivoColetado.id
#     except Exception as e:
#         print(e)
#         arquivoColetado.status = "ERROR"
#         arquivoColetado.msg = str(e)
#         arquivoColetado.save()
#         raise
    
# @shared_task(
#     bind=True,
# )
# def task_carregar_vinc_pub(
#     self,
#     id_arquivoColetado : int,
# ):
#     arquivoColetado = ArquivoColetado.objects.get(id=id_arquivoColetado)
#     try:
#         carregar_vinc_pub(arquivoColetado)
#         return arquivoColetado.id
#     except Exception as e:
#         print(e)
#         arquivoColetado.status = "ERROR"
#         arquivoColetado.msg = str(e)
#         arquivoColetado.save()
#         raise

# @shared_task(
#     bind=True,
# )
# def task_carregar_estab_pub(
#     self,
#     id_arquivoColetado : int,
# ):
#     arquivoColetado = ArquivoColetado.objects.get(id=id_arquivoColetado)
#     try:
#         carregar_estab_pub(arquivoColetado)
#         return arquivoColetado.id
#     except Exception as e:
#         print(e)
#         arquivoColetado.status = "ERROR"
#         arquivoColetado.msg = str(e)
#         arquivoColetado.save()
#         raise

# RAIS_VINC_PUB_MG_ES_RJ.7z    
@shared_task(
    bind=True,
)
def task_coletar_vinc_pub(
    self,
    ano: int
    ):
    
    arquivo_nome = "RAIS_VINC_PUB_MG_ES_RJ.7z"
    arquivo_coletado, _ = ArquivoColetado.objects.get_or_create(
        nome=arquivo_nome,
        ano=ano,
    )
    arquivo_coletado.status = "PENDING"
    arquivo_coletado.save()
    
    try:
        baixar_rais(arquivoColetado=arquivo_coletado) 
        registrar_log(
            operacao="DOWNLOAD",
            arquivo=arquivo_nome,
            data_referencia=str(ano),
            sucesso=True,
        )    
    except Exception as e:
        arquivo_coletado.status = "FAILED"
        arquivo_coletado.msg = str(e)
        arquivo_coletado.save()
        registrar_log(
            operacao="DOWNLOAD",
            arquivo=arquivo_nome,
            data_referencia=str(ano),
            sucesso=False,
            erro=str(e),
        )
        raise 
    
    # id_arquivo_coletado = task_baixar_rais.apply(
    #                         kwargs={
    #                             'ano':ano,
    #                             'nome_arquivo_servidor':"RAIS_VINC_PUB_MG_ES_RJ.7z"
    #                         }
    #                     ).result
    
    # arquivo = ArquivoColetado.objects.get(id=id_arquivo_coletado)
    
    try:
        filtrar_vinc_pub(arquivo_coletado)
        registrar_log(
            operacao="FILTRO",
            arquivo=arquivo_nome,
            data_referencia=str(ano),
            sucesso=True,
        )
    except Exception as e:
        print(e)
        arquivo_coletado.status = "ERROR"
        arquivo_coletado.msg = str(e)
        arquivo_coletado.save()
        registrar_log(
            operacao="FILTRO",
            arquivo=arquivo_nome,
            data_referencia=str(ano),
            sucesso=False,
            erro=str(e),
        )
        raise

    try:
        carregar_vinc_pub(arquivo_coletado)
        registrar_log(
            operacao="CARGA",
            arquivo=arquivo_nome,
            data_referencia=str(ano),
            sucesso=True,
        )
    except Exception as e:
        print(e)
        arquivo_coletado.status = "ERROR"
        arquivo_coletado.msg = str(e)
        arquivo_coletado.save()
        registrar_log(
            operacao="CARGA",
            arquivo=arquivo_nome,
            data_referencia=str(ano),
            sucesso=False,
            erro=str(e),
        )
        raise

    
# RAIS_ESTAB_PUB.7z   
@shared_task(
    bind=True,
)
def task_coletar_estab_pub(
    self,
    ano: int
    ):
    
    arquivo_nome = "RAIS_ESTAB_PUB.7z"
    arquivo_coletado, _ = ArquivoColetado.objects.get_or_create(
        nome=arquivo_nome,
        ano=ano,
    )
    arquivo_coletado.status = "PENDING"
    arquivo_coletado.save()
    
    try:
        baixar_rais(arquivoColetado=arquivo_coletado) 
        registrar_log(
            operacao="DOWNLOAD",
            arquivo=arquivo_nome,
            data_referencia=str(ano),
            sucesso=True,
        )    
    except Exception as e:
        arquivo_coletado.status = "FAILED"
        arquivo_coletado.msg = str(e)
        arquivo_coletado.save()
        registrar_log(
            operacao="DOWNLOAD",
            arquivo=arquivo_nome,
            data_referencia=str(ano),
            sucesso=False,
            erro=str(e),
        )
        raise 

    try:
        filtrar_estab_pub(arquivo_coletado)
        registrar_log(
            operacao="FILTRO",
            arquivo=arquivo_nome,
            data_referencia=str(ano),
            sucesso=True,
        )
    except Exception as e:
        print(e)
        arquivo_coletado.status = "ERROR"
        arquivo_coletado.msg = str(e)
        arquivo_coletado.save()
        registrar_log(
            operacao="FILTRO",
            arquivo=arquivo_nome,
            data_referencia=str(ano),
            sucesso=False,
            erro=str(e),
        )
        raise
    
    try:
        carregar_estab_pub(arquivo_coletado)
        registrar_log(
            operacao="CARGA",
            arquivo=arquivo_nome,
            data_referencia=str(ano),
            sucesso=True,
        )
    except Exception as e:
        print(e)
        arquivo_coletado.status = "ERROR"
        arquivo_coletado.msg = str(e)
        arquivo_coletado.save()
        registrar_log(
            operacao="CARGA",
            arquivo=arquivo_nome,
            data_referencia=str(ano),
            sucesso=False,
            erro=str(e),
        )
        raise

@shared_task(
    bind=True,
)
def task_carregar_saldos_mensais(
    self,
    ano: int
    ):
    try:
        carregar_saldos_mensais(ano)
        registrar_log(
            operacao="CARGA",
            arquivo="SALDOS_MENSAIS",
            data_referencia=str(ano),
            sucesso=True,
        )
    except Exception as e:
        print(e)
        registrar_log(
            operacao="CARGA",
            arquivo="SALDOS_MENSAIS",
            data_referencia=str(ano),
            sucesso=False,
            erro=str(e),
        )
        raise

@shared_task(
    bind=True,
)
def task_finalizar_coleta_rais(
        self,
        ano: int,
    ):
    registrar_log(
        operacao="FINALIZACAO",
        arquivo="RAIS",
        data_referencia=str(ano),
        sucesso=True,
    )
    print("Coleta dos arquivos RAIS finalizada.")

@shared_task(
    bind=True,
)
def task_coletar_arquivos_rais(
    self,
    **kwargs,
):
    if "ano" in kwargs:
        ano = kwargs["ano"]
    else:
        ano = str(date.today().year)
        
    ch = chain(
        task_coletar_vinc_pub.si(ano=ano),
        task_coletar_estab_pub.si(ano=ano),
        task_carregar_saldos_mensais.si(ano=ano),
        task_finalizar_coleta_rais.si(ano=ano),
    )
    async_result = ch.apply_async()
    print(f"Coleta dos arquivos RAIS {ano} disparada: {async_result.id}")


@shared_task(
    bind=True,
)
def task_baixar_caged(
    self,
    ano: int,
    mes: int,
    nome_arquivo_servidor : str,
    ):
           
    arquivo_coletado, _ = ArquivoColetado.objects.get_or_create(
        nome=nome_arquivo_servidor,
        ano=ano,
        mes=mes,
    )
    arquivo_coletado.status = "PENDING"
    arquivo_coletado.save()
    try:
        baixar_caged(arquivoColetado=arquivo_coletado)
        
    except Exception as e:
        arquivo_coletado.status = "FAILED"
        arquivo_coletado.msg = str(e)
        arquivo_coletado.save()
        raise
    
    return arquivo_coletado.id

# @shared_task(
#     bind=True,
# )
# def task_filtrar_caged(
#     self,
#     id_arquivoColetado : int,
# ):
#     arquivoColetado = ArquivoColetado.objects.get(id=id_arquivoColetado)
#     try:
#         filtrar_caged(arquivoColetado)
#         return arquivoColetado.id
#     except Exception as e:
#         print(e)
#         arquivoColetado.status = "ERROR"
#         arquivoColetado.msg = str(e)
#         arquivoColetado.save()
#         raise

# @shared_task(
#     bind=True,
# )
# def task_carregar_caged_mov(
#     self,
#     id_arquivoColetado : int,
# ):
#     arquivoColetado = ArquivoColetado.objects.get(id=id_arquivoColetado)
#     try:
#         carregar_caged_mov(arquivoColetado)
#         return arquivoColetado.id
#     except Exception as e:
#         print(e)
#         arquivoColetado.status = "ERROR"
#         arquivoColetado.msg = str(e)
#         arquivoColetado.save()
#         raise
    
# @shared_task(
#     bind=True,
# )
# def task_carregar_caged_for(
#     self,
#     id_arquivoColetado : int,
# ):
#     arquivoColetado = ArquivoColetado.objects.get(id=id_arquivoColetado)
#     try:
#         carregar_caged_for(arquivoColetado)
#         return arquivoColetado.id
#     except Exception as e:
#         print(e)
#         arquivoColetado.status = "ERROR"
#         arquivoColetado.msg = str(e)
#         arquivoColetado.save()
#         raise

# @shared_task(
#     bind=True,
# )
# def task_carregar_caged_exc(
#     self,
#     id_arquivoColetado : int,
# ):
#     arquivoColetado = ArquivoColetado.objects.get(id=id_arquivoColetado)
#     try:
#         carregar_caged_exc(arquivoColetado)
#         return arquivoColetado.id
#     except Exception as e:
#         print(e)
#         arquivoColetado.status = "ERROR"
#         arquivoColetado.msg = str(e)
#         arquivoColetado.save()
#         raise
    
@shared_task(
    bind=True,
)
def task_coletar_caged_mov(
    self,
    ano: int,
    mes: int,
):
    
    arquivo_nome = "CAGEDMOV"
    data_referencia = f"{ano:04d}-{mes:02d}"
    arquivo_coletado, _ = ArquivoColetado.objects.get_or_create(
            nome=arquivo_nome,
            ano=ano,
            mes=mes,
        )
    
    arquivo_coletado.status = "PENDING"
    arquivo_coletado.save()
    
    try:
        baixar_caged(arquivoColetado=arquivo_coletado)    
        
        registrar_log(
                operacao="DOWNLOAD",
                arquivo=arquivo_nome,
                data_referencia=data_referencia,
                sucesso=True,
            )
        
    except Exception as e:
        arquivo_coletado.status = "FAILED"
        arquivo_coletado.msg = str(e)
        arquivo_coletado.save()
        
        registrar_log(
            operacao="DOWNLOAD",
            arquivo=arquivo_nome,
            data_referencia=data_referencia,
            sucesso=False,
            erro=str(e),
        )
        
        raise
       
    # id_arquivo_coletado = task_baixar_caged.apply(
    #                         kwargs={
    #                             'ano':ano,
    #                             'mes':mes,
    #                             'nome_arquivo_servidor':f"CAGEDMOV",
    #                         }
    #                     ).result
    
    # arquivo = ArquivoColetado.objects.get(id = id_arquivo_coletado)
    
    try:
        filtrar_caged(arquivo_coletado)
        
        registrar_log(
            operacao="FILTRO",
            arquivo=arquivo_nome,
            data_referencia=data_referencia,
            sucesso=True,
        )
        
    except Exception as e:
        print(e)
        arquivo_coletado.status = "ERROR"
        arquivo_coletado.msg = str(e)
        arquivo_coletado.save()
        
        registrar_log(
            operacao="FILTRO",
            arquivo=arquivo_nome,
            data_referencia=data_referencia,
            sucesso=False,
            erro=str(e),
        )
        raise
 
    try:
        carregar_caged_mov(arquivo_coletado)
        
        registrar_log(
            operacao="CARGA",
            arquivo=arquivo_nome,
            data_referencia=data_referencia,
            sucesso=True,
        )
        
    except Exception as e:
        print(e)
        arquivo_coletado.status = "ERROR"
        arquivo_coletado.msg = str(e)
        arquivo_coletado.save()
        
        registrar_log(
            operacao="CARGA",
            arquivo=arquivo_nome,
            data_referencia=data_referencia,
            sucesso=False,
            erro=str(e),
        )
        raise
    

@shared_task(
    bind=True,
)
def task_coletar_caged_for(
    self,
    ano: int,
    mes: int,
):
    arquivo_nome = "CAGEDFOR"
    data_referencia = f"{ano:04d}-{mes:02d}"
    arquivo_coletado, _ = ArquivoColetado.objects.get_or_create(
            nome=arquivo_nome,
            ano=ano,
            mes=mes,
        )
    
    arquivo_coletado.status = "PENDING"
    arquivo_coletado.save()
    
    try:
        baixar_caged(arquivoColetado=arquivo_coletado)
        
        registrar_log(
                operacao="DOWNLOAD",
                arquivo=arquivo_nome,
                data_referencia=data_referencia,
                sucesso=True,
            )
            
    except Exception as e:
        
        if(str(e).startswith("550")): # arquivo não encontrado
            print(f"Arquivo CAGED FOR {ano}-{mes} não encontrado. Pulando etapa de coleta.")
            
            registrar_log(
                operacao="DOWNLOAD",
                arquivo=arquivo_nome,
                data_referencia=data_referencia,
                sucesso=False,
                erro=f"{e} + Arquivo não encontrado. Pulando etapa de coleta.",
            )
            return None
        else:
            registrar_log(
                operacao="DOWNLOAD",
                arquivo=arquivo_nome,
                data_referencia=data_referencia,
                sucesso=False,
                erro=str(e),
            )
            raise e        
    
    try:
        filtrar_caged(arquivo_coletado)
        
        registrar_log(
            operacao="FILTRO",
            arquivo=arquivo_nome,
            data_referencia=data_referencia,
            sucesso=True,
        )
    except Exception as e:
        print(e)
        arquivo_coletado.status = "ERROR"
        arquivo_coletado.msg = str(e)
        arquivo_coletado.save()
        registrar_log(
            operacao="FILTRO",
            arquivo=arquivo_nome,
            data_referencia=data_referencia,
            sucesso=False,
            erro=str(e),
        )
        raise
    
    try:
        carregar_caged_for(arquivo_coletado)
        registrar_log(
            operacao="CARGA",
            arquivo=arquivo_nome,
            data_referencia=data_referencia,
            sucesso=True,
        )
    except Exception as e:
        print(e)
        arquivo_coletado.status = "ERROR"
        arquivo_coletado.msg = str(e)
        arquivo_coletado.save()
        registrar_log(
            operacao="CARGA",
            arquivo=arquivo_nome,
            data_referencia=data_referencia,
            sucesso=False,
            erro=str(e),
        )
        raise


@shared_task(
    bind=True,
)
def task_coletar_caged_exc(
    self,
    ano: int,
    mes: int,
):
    arquivo_nome = "CAGEDEXC"
    data_referencia = f"{ano:04d}-{mes:02d}"
    arquivo_coletado, _ = ArquivoColetado.objects.get_or_create(
            nome=arquivo_nome,
            ano=ano,
            mes=mes,
        )
    
    arquivo_coletado.status = "PENDING"
    arquivo_coletado.save()
    
    try:
        baixar_caged(arquivoColetado=arquivo_coletado)
        registrar_log(
                operacao="DOWNLOAD",
                arquivo=arquivo_nome,
                data_referencia=data_referencia,
                sucesso=True,
            )
    except Exception as e:
        if(str(e).startswith("550")): # arquivo não encontrado
            print(f"Arquivo CAGED EXC {ano}-{mes} não encontrado. Pulando etapa de coleta.")
            registrar_log(
                operacao="DOWNLOAD",
                arquivo=arquivo_nome,
                data_referencia=data_referencia,
                sucesso=False,
                erro=f"{e} + Arquivo não encontrado. Pulando etapa de coleta.",
            )
            return None
        else:
            registrar_log(
                operacao="DOWNLOAD",
                arquivo=arquivo_nome,
                data_referencia=data_referencia,
                sucesso=False,
                erro=str(e),
            )
            raise e
    
    try:
        filtrar_caged(arquivo_coletado)
        registrar_log(
            operacao="FILTRO",
            arquivo=arquivo_nome,
            data_referencia=data_referencia,
            sucesso=True,
        )
    except Exception as e:
        print(e)
        arquivo_coletado.status = "ERROR"
        arquivo_coletado.msg = str(e)
        arquivo_coletado.save()
        registrar_log(
            operacao="FILTRO",
            arquivo=arquivo_nome,
            data_referencia=data_referencia,
            sucesso=False,
            erro=str(e),
        )
        raise   

    try:
        carregar_caged_exc(arquivo_coletado)
        registrar_log(
            operacao="CARGA",
            arquivo=arquivo_nome,
            data_referencia=data_referencia,
            sucesso=True,
        )
    except Exception as e:
        print(e)
        arquivo_coletado.status = "ERROR"
        arquivo_coletado.msg = str(e)
        arquivo_coletado.save()
        registrar_log(
            operacao="CARGA",
            arquivo=arquivo_nome,
            data_referencia=data_referencia,
            sucesso=False,
            erro=str(e),
        )
        raise   
 
    
@shared_task(
    bind=True,
)
def task_carregar_saldos_mensais_temporarios(
    self,
    year:int,
    month:int,
):
    data_referencia = f"{year:04d}-{month:02d}"
    try:
        carregar_saldos_mensais_temporarios(year, month)
        registrar_log(
            operacao="CARGA_SALDOS_MENS_TEMP",
            arquivo="",
            data_referencia=data_referencia,
            sucesso=True,
        )
    except Exception as e:
        print(e)
        registrar_log(
            operacao="CARGA_SALDOS_MENS_TEMP",
            arquivo="",
            data_referencia=data_referencia,
            sucesso=True,
        )
        raise 


@shared_task(
    bind=True,
)
def task_finalizar_coleta_caged(
        self,
        ano: int,
        mes: int,
    ):
    registrar_log(
        operacao="FINALIZACAO",
        arquivo="CAGED",
        data_referencia=f"{ano:04d}-{mes:02d}",
        sucesso=True,
    )
    print("Coleta dos arquivos CAGED finalizada.")


@shared_task(bind=True)
def task_coletar_arquivos_caged(self, **kwargs):
    # =========================
    # MODO MANUAL: ano/mes explícitos
    # =========================
    if "ano" in kwargs and "mes" in kwargs:
        ano = kwargs["ano"]
        mes = kwargs["mes"]

        ch = chain(
            task_coletar_caged_mov.si(ano=ano, mes=mes),
            task_coletar_caged_for.si(ano=ano, mes=mes),
            task_coletar_caged_exc.si(ano=ano, mes=mes),
            task_carregar_saldos_mensais_temporarios.si(year=ano, month=mes),
            task_finalizar_coleta_caged.si(ano=ano, mes=mes),
        )
        async_result = ch.apply_async()
        print(f"Coleta dos arquivos CAGED {ano}-{mes:02d} disparada: {async_result.id}")
        return

    # =========================
    # MODO AUTOMÁTICO: intervalo de meses
    # =========================
    # 1. Último registro em SaldoMensalCaged
    ultimo = SaldoMensalCaged.objects.aggregate(
        ultimo_referencia=Max("referencia")
    )["ultimo_referencia"]

    if ultimo is None:
        # Sem nenhum registro: define um ponto de partida (ajuste conforme sua regra)
        ultimo = date(date.today().year, 1, 1)

    # 2. Mês mais recente (já coletado)
    mes_mais_recente = ultimo.replace(day=1)

    # 3. Primeiro mês a processar = mês seguinte
    data_inicio = mes_mais_recente + relativedelta(months=1)

    # 4. Mês limite = mês atual - 2
    hoje = date.today()
    mes_atual_inicio = hoje.replace(day=1)
    mes_limite = mes_atual_inicio - relativedelta(months=2)

    # 5. Se o primeiro mês já for maior que o limite, não há nada a processar
    if data_inicio > mes_limite:
        print(
            f"Não há meses para processar: "
            f"primeiro_mês={data_inicio}, limite={mes_limite}"
        )
        return

    # 6. Gerar lista de meses (ano, mes) entre data_inicio e mes_limite (inclusive)
    meses_a_processar = []
    current = data_inicio
    while current <= mes_limite:
        meses_a_processar.append((current.year, current.month))
        current = current + relativedelta(months=1)

    # 7. Construir uma chain única, onde cada elo é a chain de um mês
    chain_de_meses = []
    for ano, mes in meses_a_processar:
        ch_mes = chain(
            task_coletar_caged_mov.si(ano=ano, mes=mes),
            task_coletar_caged_for.si(ano=ano, mes=mes),
            task_coletar_caged_exc.si(ano=ano, mes=mes),
            task_carregar_saldos_mensais_temporarios.si(year=ano, month=mes),
            task_finalizar_coleta_caged.si(ano=ano, mes=mes),
        )
        chain_de_meses.append(ch_mes)

    # Chain geral: meses em sequência
    chain_geral = chain(*chain_de_meses)
    async_result = chain_geral.apply_async()

    print(
        f"Coleta CAGED em sequência disparada para os meses "
        f"{meses_a_processar}: {async_result.id}"
    )