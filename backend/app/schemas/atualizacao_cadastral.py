from datetime import datetime
import re

from pydantic import BaseModel, ConfigDict


class AtualizacaoCadastralOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    protocolo: str
    nome_empresarial: str
    cnpj: str
    endereco: str
    email: str
    telefone: str
    ramo_atividade: str
    previsao_geracao_empregos: str
    representante_nome: str
    representante_cpf: str
    representante_telefone: str
    representante_email: str
    termo_empresa_aceito: bool
    termo_codego_aceito: bool
    email_enviado: bool | None
    data_envio: datetime


class AtualizacaoCadastralResponse(BaseModel):
    processo: AtualizacaoCadastralOut
    email_enviado: bool
    email_destinatario: str
    email_erro: str | None = None
    pdf_download_url: str


def validar_cnpj(v: str) -> str:
    digits = "".join(filter(str.isdigit, v))
    if len(digits) != 14:
        raise ValueError("CNPJ deve ter 14 dígitos.")
    return digits


def validar_cpf(v: str) -> str:
    digits = "".join(filter(str.isdigit, v))
    if len(digits) != 11:
        raise ValueError("CPF deve ter 11 dígitos.")
    return digits


def validar_telefone(v: str) -> str:
    digits = "".join(filter(str.isdigit, v))
    if len(digits) < 10:
        raise ValueError("Telefone deve ter DDD + número (mínimo 10 dígitos).")
    return digits


# Letras (com acentos), números, espaço, e pontuação comum de nomes/endereços/
# descrições (vírgula, ponto, hífen, barra, "&", parênteses, apóstrofo).
_PADRAO_TEXTO_SEGURO = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ0-9\s.,\-/&()'ºª]+$")

# Símbolos claramente fora do padrão de nomes/endereços/descrições em
# português (o oposto do padrão acima, só pra montar uma mensagem melhor).
_CARACTERES_PROIBIDOS = re.compile(r"[^A-Za-zÀ-ÖØ-öø-ÿ0-9\s.,\-/&()'ºª]")


def validar_texto_seguro(v: str, nome_campo: str, tamanho_max_palavra: int = 40) -> str:
    """
    Garante que o campo não contenha caracteres especiais (@, #, $, %, etc.) e
    que não tenha uma sequência gigante sem espaços (o que quebraria o layout
    do PDF gerado). Usado nos campos de texto livre do formulário.
    """
    valor = v.strip()

    caracteres_invalidos = sorted(set(_CARACTERES_PROIBIDOS.findall(valor)))
    if caracteres_invalidos:
        raise ValueError(
            f"O campo '{nome_campo}' contém caracteres não permitidos: "
            f"{' '.join(caracteres_invalidos)}"
        )

    for palavra in valor.split():
        if len(palavra) > tamanho_max_palavra:
            raise ValueError(
                f"O campo '{nome_campo}' contém um texto muito longo sem espaços."
            )

    return valor
