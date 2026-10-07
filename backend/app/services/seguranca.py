import hashlib
import hmac
import logging
import secrets

from app.config import settings

logger = logging.getLogger("codego.seguranca")

_SEGREDO_PADRAO = "change_me_secret"

# Chave usada para assinar os links de download do PDF. Vem de APP_SECRET_KEY.
# Se alguém esquecer de trocar o valor padrão, usamos uma chave aleatória só
# deste processo (os links antigos deixam de valer ao reiniciar, o que não
# atrapalha: o link só é usado logo depois do envio do formulário). Assim um
# valor padrão conhecido nunca permite forjar links.
if not settings.app_secret_key or settings.app_secret_key == _SEGREDO_PADRAO:
    logger.warning(
        "APP_SECRET_KEY está com o valor padrão; usando uma chave aleatória temporária. "
        "Defina um valor longo e secreto no Render (Environment)."
    )
    _CHAVE = secrets.token_bytes(32)
else:
    _CHAVE = settings.app_secret_key.encode("utf-8")


def gerar_token_download(protocolo: str) -> str:
    """Token que só quem recebeu a resposta do envio conhece (HMAC do protocolo)."""
    return hmac.new(_CHAVE, protocolo.encode("utf-8"), hashlib.sha256).hexdigest()


def token_download_valido(protocolo: str, token: str) -> bool:
    if not token:
        return False
    return hmac.compare_digest(gerar_token_download(protocolo), token)
