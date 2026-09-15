import logging
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from app.config import settings

logger = logging.getLogger("codego.email")


def enviar_email_atualizacao_cadastral(
    destinatario_email: str,
    nome_empresarial: str,
    protocolo: str,
    caminhos_anexos: list[str],
) -> tuple[bool, str | None]:
    """
    Envia um e-mail de confirmação de recebimento da atualização cadastral, com
    os documentos em anexo (compactados em um .zip). Escolhe a implementação conforme
    settings.email_provider ("smtp", "outlook_graph" ou "formsubmit"). Retorna
    (True, None) se o envio foi bem-sucedido, ou (False, mensagem_de_erro)
    caso contrário — nunca levanta exceção.
    """
    if settings.email_provider == "outlook_graph":
        from app.services.outlook_email_service import enviar_email_atualizacao_cadastral_outlook

        return enviar_email_atualizacao_cadastral_outlook(
            destinatario_email, nome_empresarial, protocolo, caminhos_anexos
        )

    if settings.email_provider == "formsubmit":
        from app.services.formsubmit_email_service import enviar_email_atualizacao_cadastral_formsubmit

        return enviar_email_atualizacao_cadastral_formsubmit(
            destinatario_email, nome_empresarial, protocolo, caminhos_anexos
        )

    return _enviar_via_smtp(destinatario_email, nome_empresarial, protocolo, caminhos_anexos)


def _montar_corpo_texto(nome_empresarial: str, protocolo: str) -> str:
    return (
        f"Olá,\n\n"
        f"Confirmamos o recebimento da solicitação de atualização cadastral da "
        f"empresa {nome_empresarial}, com os documentos em anexo "
        f"(compactados em um único arquivo .zip).\n\n"
        f"Protocolo: {protocolo}\n\n"
        f"Este e-mail confirma que os dados e arquivos foram recebidos pelo "
        f"Sistema de Atualização Cadastral CODEGO.\n\n"
        f"Atenciosamente,\n"
        f"Companhia de Desenvolvimento Econômico de Goiás"
    )


def _montar_corpo_html(nome_empresarial: str, protocolo: str) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; color: #1a1a1a; font-size: 14px; line-height: 1.6;">
      <p>Olá,</p>
      <p>
        Confirmamos o recebimento da solicitação de atualização cadastral da empresa
        <strong>{nome_empresarial}</strong>, com os documentos em anexo (compactados em um único arquivo .zip).
      </p>
      <p style="font-family: monospace; background: #f2f2f2; padding: 8px 12px; display: inline-block;">
        Protocolo: <strong>{protocolo}</strong>
      </p>
      <p>
        Este e-mail confirma que os dados e arquivos foram recebidos pelo
        <strong>Sistema de Atualização Cadastral CODEGO</strong>.
      </p>
      <p>Atenciosamente,<br>Companhia de Desenvolvimento Econômico de Goiás</p>
    </div>
    """


def _enviar_via_smtp(
    destinatario_email: str,
    nome_empresarial: str,
    protocolo: str,
    caminhos_anexos: list[str],
) -> tuple[bool, str | None]:
    if not settings.smtp_enabled:
        motivo = "Envio de e-mail desabilitado (SMTP_ENABLED=false)."
        logger.info(motivo)
        return False, motivo

    if not settings.smtp_user or not settings.smtp_password:
        motivo = "SMTP_USER/SMTP_PASSWORD não configurados."
        logger.warning(motivo)
        return False, motivo

    remetente = settings.smtp_from_email or settings.smtp_user

    mensagem = MIMEMultipart("mixed")
    mensagem["Subject"] = f"Atualização cadastral recebida — Protocolo {protocolo}"
    mensagem["From"] = formataddr((settings.smtp_from_name, remetente))
    mensagem["To"] = destinatario_email

    corpo_alternativo = MIMEMultipart("alternative")
    corpo_alternativo.attach(MIMEText(_montar_corpo_texto(nome_empresarial, protocolo), "plain", "utf-8"))
    corpo_alternativo.attach(MIMEText(_montar_corpo_html(nome_empresarial, protocolo), "html", "utf-8"))
    mensagem.attach(corpo_alternativo)

    for caminho in caminhos_anexos:
        try:
            with open(caminho, "rb") as f:
                subtipo = os.path.splitext(caminho)[1].lstrip(".").lower() or "octet-stream"
                anexo = MIMEApplication(f.read(), _subtype=subtipo)
                anexo.add_header(
                    "Content-Disposition", "attachment", filename=os.path.basename(caminho)
                )
                mensagem.attach(anexo)
        except OSError as erro:
            logger.warning("Não foi possível anexar o arquivo %s: %s", caminho, erro)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as servidor:
            if settings.smtp_use_tls:
                servidor.starttls()
            servidor.login(settings.smtp_user, settings.smtp_password)
            servidor.sendmail(remetente, [destinatario_email], mensagem.as_string())
        logger.info("E-mail de confirmação enviado para %s (protocolo %s).", destinatario_email, protocolo)
        return True, None
    except Exception as erro:  # noqa: BLE001 — falha de e-mail não pode derrubar o envio
        logger.exception("Falha ao enviar e-mail de confirmação")
        return False, f"{type(erro).__name__}: {erro}"
