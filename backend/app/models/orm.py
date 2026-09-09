from sqlalchemy import Column, Integer, String, Boolean, DateTime, func

from app.database import Base


class AtualizacaoCadastral(Base):
    __tablename__ = "atualizacoes_cadastrais"

    id = Column(Integer, primary_key=True, index=True)
    protocolo = Column(String(50), nullable=False, unique=True, index=True)

    # Dados da empresa
    nome_empresarial = Column(String(255), nullable=False)
    cnpj = Column(String(20), nullable=False, index=True)
    endereco = Column(String(500), nullable=False)
    distrito = Column(String(255), nullable=False)
    telefone = Column(String(30), nullable=False)
    email = Column(String(255), nullable=False)

    # Representante legal
    representante_nome = Column(String(255), nullable=False)
    representante_cpf = Column(String(20), nullable=False)
    representante_cargo = Column(String(100), nullable=False)

    # Termos aceitos
    termo_empresa_aceito = Column(Boolean, nullable=False, default=False)
    termo_codego_aceito = Column(Boolean, nullable=False, default=False)

    # Arquivos anexados
    caminho_pdf_cnpj = Column(String(500), nullable=False)
    caminho_pdf_contrato_social = Column(String(500), nullable=False)

    # Confirmação por e-mail
    email_enviado = Column(Boolean, nullable=True)

    data_envio = Column(DateTime, server_default=func.now())
