-- Schema inicial: Sistema de Atualização Cadastral CODEGO

CREATE TABLE IF NOT EXISTS atualizacoes_cadastrais (
    id INT AUTO_INCREMENT PRIMARY KEY,
    protocolo VARCHAR(50) NOT NULL UNIQUE,

    nome_empresarial VARCHAR(255) NOT NULL,
    cnpj VARCHAR(20) NOT NULL,
    endereco VARCHAR(500) NOT NULL,
    distrito VARCHAR(255) NOT NULL,
    telefone VARCHAR(30) NOT NULL,
    email VARCHAR(255) NOT NULL,

    representante_nome VARCHAR(255) NOT NULL,
    representante_cpf VARCHAR(20) NOT NULL,
    representante_cargo VARCHAR(100) NOT NULL,

    termo_empresa_aceito BOOLEAN NOT NULL DEFAULT FALSE,
    termo_codego_aceito BOOLEAN NOT NULL DEFAULT FALSE,

    caminho_pdf_cnpj VARCHAR(500) NOT NULL,
    caminho_pdf_contrato_social VARCHAR(500) NOT NULL,

    email_enviado BOOLEAN NULL,

    data_envio DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_cnpj (cnpj)
);
