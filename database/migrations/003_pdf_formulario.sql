-- Migração: adiciona o campo "Previsão de geração de empregos" e o caminho
-- do PDF timbrado gerado a partir dos dados do formulário preenchido.

ALTER TABLE atualizacoes_cadastrais
    ADD COLUMN previsao_geracao_empregos VARCHAR(255) NOT NULL DEFAULT '' AFTER ramo_atividade,
    ADD COLUMN caminho_pdf_formulario VARCHAR(500) NOT NULL DEFAULT '' AFTER termo_codego_aceito;
