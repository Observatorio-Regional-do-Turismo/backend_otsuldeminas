from django.conf import settings
from django.core.mail import send_mail
import logging
from .models import LogOperacao

logger = logging.getLogger(__name__)

def registrar_log(
    *,
    operacao: str,
    arquivo: str,
    data_referencia: str,
    sucesso: bool,
    erro: str = "",
):
    log = LogOperacao.objects.create(
        operacao=operacao,
        arquivo=arquivo,
        data_referencia=data_referencia,
        sucesso=sucesso,
        erro=erro or "",
    )

    if not sucesso:
        enviar_email_log(
            operacao=operacao,
            arquivo=arquivo,
            data_referencia=data_referencia,
            erro=erro,
        )

    return log


def enviar_email_log(
    *,
    operacao: str,
    arquivo: str,
    data_referencia: str,
    erro: str = "",
) -> None:
    mensagem = (
        f"Operação: {operacao}\n"
        f"Arquivo: {arquivo}\n"
        f"Data de referência: {data_referencia}\n"
        f"Status: FALHA\n"
        f"Erro: {erro or 'Erro não informado'}\n"
    )

    try:
        send_mail(
            subject=f"[FALHA] {operacao} CAGED - {arquivo}",
            message=mensagem,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.EMAIL_NOTIFICATION_TO],
            fail_silently=False,
        )

    except Exception:
        logger.exception(
            "Não foi possível enviar o e-mail de falha "
            "da operação %s para o arquivo %s",
            operacao,
            arquivo,
        )