import logging
import os

import requests

logger = logging.getLogger("codego.email")

# O endpoint /ajax/ retorna sucesso mas descarta o anexo silenciosamente —
# só o endpoint "normal" (sem /ajax/) de fato inclui o anexo no e-mail.
# Em compensação, ele responde com uma página HTML em vez de JSON.
FORMSUBMIT_URL = "https://formsubmit.co/{email}"
_MARCADOR_SUCESSO = "submitted successfully"

# O FormSubmit rejeita requisições sem Referer/Origin de página web (proteção
# anti-bot) — como este é um envio feito pelo backend, e não por um
# navegador, simulamos esses cabeçalhos.
_HEADERS = {
    "Referer": "https://atualizacao-cadastral-0cay.onrender.com/",
    "Origin": "https://atualizacao-cadastral-0cay.onrender.com",
}


def enviar_email_atualizacao_cadastral_formsubmit(
    destinatario_email: str,
    nome_empresarial: str,
    protocolo: str,
    caminhos_anexos: list[str],
) -> tuple[bool, str | None]:
    """
    Envia a notificação de atualização cadastral via FormSubmit (HTTPS), com
    os documentos em anexo. Usado no lugar do SMTP quando a rede de
    hospedagem bloqueia conexões SMTP de saída (ex.: Render free tier).

    Na primeira vez que um e-mail de destino é usado, o FormSubmit manda um
    link de confirmação pra essa caixa de entrada — os envios só chegam de
    fato depois desse e-mail ser confirmado. Essa ativação é feita pra uma
    combinação específica (e-mail + nomes exatos dos campos enviados) — por
    isso os nomes de campo abaixo ("_subject", "_captcha", "mensagem") não
    podem mudar sem ativar de novo.
    """
    url = FORMSUBMIT_URL.format(email=destinatario_email)

    dados = {
        "_subject": f"Atualização cadastral recebida — Protocolo {protocolo}",
        "_captcha": "false",
        "mensagem": (
            f"Confirmamos o recebimento da solicitação de atualização cadastral da "
            f"empresa {nome_empresarial}, protocolo {protocolo}. Documentos em anexo "
            f"(compactados em um único arquivo .zip)."
        ),
    }

    arquivos_para_upload = []
    arquivos_abertos = []
    try:
        for caminho in caminhos_anexos:
            f = open(caminho, "rb")
            arquivos_abertos.append(f)
            arquivos_para_upload.append(
                ("attachment", (os.path.basename(caminho), f, "application/zip"))
            )

        resposta = requests.post(
            url, data=dados, files=arquivos_para_upload, headers=_HEADERS, timeout=20
        )

        # O FormSubmit responde HTTP 200 mesmo em caso de falha lógica (ex.:
        # formulário não ativado) — o resultado real vem do conteúdo da
        # página HTML retornada, não só do status HTTP.
        sucesso = resposta.ok and _MARCADOR_SUCESSO in resposta.text

        if sucesso:
            logger.info(
                "E-mail (FormSubmit) enviado para %s (protocolo %s).", destinatario_email, protocolo
            )
            return True, None

        motivo = f"FormSubmit retornou HTTP {resposta.status_code}: {resposta.text[:300]}"
        logger.warning(motivo)
        return False, motivo
    except Exception as erro:  # noqa: BLE001 — falha de e-mail não pode derrubar o envio
        logger.exception("Falha ao enviar e-mail via FormSubmit")
        return False, f"{type(erro).__name__}: {erro}"
    finally:
        for f in arquivos_abertos:
            f.close()
