-- Migração: reestrutura os campos para bater com o formulário oficial
-- (Microsoft Forms) - adiciona Ramo de Atividade, Telefone/E-mail do
-- representante, e os 3 novos uploads; remove Distrito (embutido no
-- Endereço) e Cargo do representante.

ALTER TABLE atualizacoes_cadastrais
    DROP COLUMN distrito,
    DROP COLUMN representante_cargo,
    ADD COLUMN ramo_atividade VARCHAR(255) NOT NULL DEFAULT '' AFTER telefone,
    ADD COLUMN representante_telefone VARCHAR(30) NOT NULL DEFAULT '' AFTER representante_cpf,
    ADD COLUMN representante_email VARCHAR(255) NOT NULL DEFAULT '' AFTER representante_telefone,
    ADD COLUMN caminho_pdf_certidao_matricula VARCHAR(500) NOT NULL DEFAULT '' AFTER caminho_pdf_contrato_social,
    ADD COLUMN caminho_pdf_contrato_ou_procuracao VARCHAR(500) NOT NULL DEFAULT '' AFTER caminho_pdf_certidao_matricula,
    ADD COLUMN caminho_pdf_documento_identidade VARCHAR(500) NOT NULL DEFAULT '' AFTER caminho_pdf_contrato_ou_procuracao;
