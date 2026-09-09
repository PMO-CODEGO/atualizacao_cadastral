from sqlalchemy import Column, Integer, String, Boolean, DateTime, func

from app.database import Base


class AtualizacaoCadastral(Base):
    __tablename__ = "atualizacoes_cadastrais"

    id = Column(Integer, primary_key=True, index=True)
    protocolo = Column(String(50), nullable=False, unique=True, index=True)

    # Dados da empresa
    nome_empresarial = Column(String(255), nullable=False)
    cnpj = Column(String(20), nullable=False, index=True)
    endereco = Column(String(500), nullable=False)  # Distrito / Logradouro / Quadra / Módulo / CEP
    email = Column(String(255), nullable=False)
    telefone = Column(String(30), nullable=False)
    ramo_atividade = Column(String(255), nullable=False)

    # Representante legal ou procurador
    representante_nome = Column(String(255), nullable=False)
    representante_cpf = Column(String(20), nullable=False)
    representante_telefone = Column(String(30), nullable=False)
    representante_email = Column(String(255), nullable=False)

    # Termos aceitos
    termo_empresa_aceito = Column(Boolean, nullable=False, default=False)
    termo_codego_aceito = Column(Boolean, nullable=False, default=False)

    # Arquivos anexados (empresa)
    caminho_pdf_cnpj = Column(String(500), nullable=False)
    caminho_pdf_contrato_social = Column(String(500), nullable=False)
    caminho_pdf_certidao_matricula = Column(String(500), nullable=False)

    # Arquivos anexados (representante legal ou procurador)
    caminho_pdf_contrato_ou_procuracao = Column(String(500), nullable=False)
    caminho_pdf_documento_identidade = Column(String(500), nullable=False)

    # Confirmação por e-mail
    email_enviado = Column(Boolean, nullable=True)

    data_envio = Column(DateTime, server_default=func.now())
