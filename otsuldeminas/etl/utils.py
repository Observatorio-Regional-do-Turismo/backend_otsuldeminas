# utils.py
from .models import LogOperacao


def registrar_log(
    *,
    operacao: str,
    arquivo: str,
    data_referencia: str,
    sucesso: bool,
    erro: str = "",
):
    return LogOperacao.objects.create(
        operacao=operacao,
        arquivo=arquivo,
        data_referencia=data_referencia,
        sucesso=sucesso,
        erro=erro or "",
    )