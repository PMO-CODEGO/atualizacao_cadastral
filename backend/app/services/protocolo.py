import random
from datetime import datetime

from app.config import settings


def gerar_protocolo() -> str:
    """Gera um protocolo no formato PREFIX-ANO-NNNNN, ex: ATC-2026-89421."""
    ano = datetime.now().year
    sufixo = random.randint(10000, 99999)
    return f"{settings.protocol_prefix}-{ano}-{sufixo}"
