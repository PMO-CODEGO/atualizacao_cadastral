import base64
import logging
import os

import requests

from app.services.outlook_auth import obter_access_token

logger = logging.getLogger("codego.email.outlook")

GRAPH_SEND_MAIL_URL = "https://graph.microsoft.com/v1.0/me/sendMail"


def _montar_corpo_html(nome_empresarial: str, protocolo: str) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; color: #1a1a1a; font-size: 14px; line-height: 1.6;">
      <p>Olá,</p>
      <p>
        Confirmamos o recebimento da solicitação de atualização cadastral da empresa
        <strong>{nome_empresarial}</strong>, com os documentos anexados (CNPJ e Contrato Social).
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


def enviar_email_atualizacao_cadastral_outlook(
    destinatario_email: str,
    nome_empresarial: str,
    protocolo: str,
    caminhos_anexos: list[str],
) -> tuple[bool, str | None]:
    """
    Envia o e-mail de confirmação via Microsoft Graph API (OAuth2), com todos os
    arquivos em caminhos_anexos anexados. Retorna (True, None) em sucesso, ou
    (False, motivo) em caso de falha — nunca levanta exceção.
    """
    access_token, erro_token = obter_access_token()
    if access_token is None:
        logger.warning("Não foi possível obter token do Outlook: %s", erro_token)
        return False, erro_token

    anexos_graph = []
    for caminho in caminhos_anexos:
        try:
            with open(caminho, "rb") as f:
                anexo_base64 = base64.b64encode(f.read()).decode("ascii")
            anexos_graph.append(
                {
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": os.path.basename(caminho),
                    "contentType": "application/pdf",
                    "contentBytes": anexo_base64,
                }
            )
        except OSError as erro:
            logger.warning("Não foi possível ler o anexo %s: %s", caminho, erro)

    corpo = {
        "message": {
            "subject": f"Atualização cadastral recebida — Protocolo {protocolo}",
            "body": {
                "contentType": "HTML",
                "content": _montar_corpo_html(nome_empresarial, protocolo),
            },
            "toRecipients": [{"emailAddress": {"address": destinatario_email}}],
        },
        "saveToSentItems": True,
    }

    if anexos_graph:
        corpo["message"]["attachments"] = anexos_graph

    try:
        resposta = requests.post(
            GRAPH_SEND_MAIL_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=corpo,
            timeout=20,
        )
        if resposta.status_code == 202:
            logger.info(
                "E-mail (Outlook/Graph) enviado para %s (protocolo %s).", destinatario_email, protocolo
            )
            return True, None

        motivo = f"HTTP {resposta.status_code}: {resposta.text[:300]}"
        logger.warning("Falha ao enviar e-mail via Graph: %s", motivo)
        return False, motivo
    except requests.RequestException as erro:
        logger.exception("Falha de rede ao enviar e-mail via Graph")
        return False, f"{type(erro).__name__}: {erro}"
