import logging
import os

import msal

from app.config import settings

logger = logging.getLogger("codego.email.outlook")

GRAPH_SCOPES = ["Mail.Send"]


def _carregar_cache() -> msal.SerializableTokenCache:
    cache = msal.SerializableTokenCache()
    if os.path.exists(settings.outlook_token_cache_path):
        with open(settings.outlook_token_cache_path, "r", encoding="utf-8") as f:
            cache.deserialize(f.read())
    return cache


def salvar_cache(cache: msal.SerializableTokenCache) -> None:
    if not cache.has_state_changed:
        return
    os.makedirs(os.path.dirname(settings.outlook_token_cache_path), exist_ok=True)
    with open(settings.outlook_token_cache_path, "w", encoding="utf-8") as f:
        f.write(cache.serialize())


def montar_app() -> msal.PublicClientApplication:
    authority = f"https://login.microsoftonline.com/{settings.outlook_tenant}"
    cache = _carregar_cache()
    app = msal.PublicClientApplication(
        client_id=settings.outlook_client_id,
        authority=authority,
        token_cache=cache,
    )
    return app


def obter_access_token() -> tuple[str | None, str | None]:
    """
    Tenta obter um access token válido para o Microsoft Graph, usando
    silenciosamente o refresh token salvo em cache (do login único feito via
    scripts/setup_outlook_auth.py). Retorna (token, None) em caso de sucesso,
    ou (None, motivo_do_erro) caso contrário.
    """
    if not settings.outlook_client_id:
        return None, "OUTLOOK_CLIENT_ID não configurado."

    if not os.path.exists(settings.outlook_token_cache_path):
        return None, (
            "Nenhuma conta Outlook autorizada ainda. Rode o script "
            "scripts/setup_outlook_auth.py para fazer o login único."
        )

    app = montar_app()
    contas = app.get_accounts()
    if not contas:
        return None, "Cache de token existe, mas nenhuma conta encontrada nele. Rode o setup novamente."

    resultado = app.acquire_token_silent(GRAPH_SCOPES, account=contas[0])
    salvar_cache(app.token_cache)

    if not resultado or "access_token" not in resultado:
        erro = (resultado or {}).get("error_description", "Falha desconhecida ao renovar o token.")
        return None, erro

    return resultado["access_token"], None
