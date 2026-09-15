import base64
import logging
import os

import requests

from app.config import settings

logger = logging.getLogger("codego.email")

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


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


def enviar_email_atualizacao_cadastral_brevo_api(
    destinatario_email: str,
    nome_empresarial: str,
    protocolo: str,
    caminhos_anexos: list[str],
) -> tuple[bool, str | None]:
    """
    Envia a notificação de atualização cadastral via API HTTPS da Brevo
    (api.brevo.com), no lugar do SMTP — usado quando a rede de hospedagem
    bloqueia conexões SMTP de saída (ex.: Render free tier).
    """
    if not settings.brevo_api_key:
        motivo = "BREVO_API_KEY não configurada."
        logger.warning(motivo)
        return False, motivo

    anexos = []
    for caminho in caminhos_anexos:
        try:
            with open(caminho, "rb") as f:
                conteudo_base64 = base64.b64encode(f.read()).decode("ascii")
            anexos.append({"content": conteudo_base64, "name": os.path.basename(caminho)})
        except OSError as erro:
            logger.warning("Não foi possível anexar o arquivo %s: %s", caminho, erro)

    payload = {
        "sender": {"name": settings.smtp_from_name, "email": settings.brevo_sender_email},
        "to": [{"email": destinatario_email}],
        "subject": f"Atualização cadastral recebida — Protocolo {protocolo}",
        "htmlContent": _montar_corpo_html(nome_empresarial, protocolo),
        "attachment": anexos,
    }

    try:
        resposta = requests.post(
            BREVO_API_URL,
            json=payload,
            headers={
                "api-key": settings.brevo_api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=30,
        )

        if resposta.status_code in (200, 201):
            logger.info(
                "E-mail (Brevo API) enviado para %s (protocolo %s).", destinatario_email, protocolo
            )
            return True, None

        motivo = f"Brevo API retornou HTTP {resposta.status_code}: {resposta.text[:300]}"
        logger.warning(motivo)
        return False, motivo
    except Exception as erro:  # noqa: BLE001 — falha de e-mail não pode derrubar o envio
        logger.exception("Falha ao enviar e-mail via Brevo API")
        return False, f"{type(erro).__name__}: {erro}"
