import base64
import os
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML, default_url_fetcher

from app.config import settings

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
# autoescape ligado: qualquer "<", ">" ou aspas digitadas no formulário viram
# texto comum no PDF, nunca HTML.
_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


def _url_fetcher_seguro(url, *args, **kwargs):
    """
    O PDF só precisa de imagens embutidas (data:). Qualquer outro recurso
    (file://, http://, https://) é bloqueado, para o WeasyPrint nunca ler
    arquivos do servidor nem acessar a rede por causa de conteúdo do formulário.
    """
    if url.startswith("data:"):
        return default_url_fetcher(url, *args, **kwargs)
    raise ValueError(f"Recurso externo bloqueado na geração do PDF: {url[:80]}")


def _carregar_brasao_base64() -> str:
    caminho = os.path.join(TEMPLATES_DIR, "assets", "brasao_codego.png")
    with open(caminho, "rb") as f:
        conteudo = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{conteudo}"


_BRASAO_DATA_URI = _carregar_brasao_base64()


def _formatar_cnpj(digits: str) -> str:
    if len(digits) != 14:
        return digits
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


def _formatar_cpf(digits: str) -> str:
    if len(digits) != 11:
        return digits
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def _formatar_telefone(digits: str) -> str:
    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    return digits


def gerar_pdf_formulario(
    protocolo: str,
    nome_empresarial: str,
    cnpj: str,
    endereco: str,
    email: str,
    telefone: str,
    ramo_atividade: str,
    previsao_geracao_empregos: str,
    representante_nome: str,
    representante_cpf: str,
    representante_telefone: str,
    representante_email: str,
) -> str:
    """
    Renderiza o formulário de atualização cadastral preenchido (timbrado, com
    todos os dados informados) e gera o PDF em disco. Retorna o caminho do
    arquivo gerado.
    """
    template = _env.get_template("formulario_atualizacao.html")

    html_renderizado = template.render(
        brasao_data_uri=_BRASAO_DATA_URI,
        protocolo=protocolo,
        data_emissao=datetime.now().strftime("Goiânia, %d/%m/%Y"),
        nome_empresarial=nome_empresarial,
        cnpj=_formatar_cnpj(cnpj),
        endereco=endereco,
        email=email,
        telefone=_formatar_telefone(telefone),
        ramo_atividade=ramo_atividade,
        previsao_geracao_empregos=previsao_geracao_empregos,
        representante_nome=representante_nome,
        representante_cpf=_formatar_cpf(representante_cpf),
        representante_telefone=_formatar_telefone(representante_telefone),
        representante_email=representante_email,
    )

    os.makedirs(settings.upload_dir, exist_ok=True)
    nome_arquivo = f"{protocolo}_formulario_atualizacao_cadastral.pdf"
    caminho_completo = os.path.join(settings.upload_dir, nome_arquivo)

    HTML(string=html_renderizado, url_fetcher=_url_fetcher_seguro).write_pdf(caminho_completo)

    return caminho_completo
