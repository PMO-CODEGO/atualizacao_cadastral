from datetime import datetime

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
