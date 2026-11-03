-- Migração: suporte a "reiniciar ciclo" sem apagar histórico.
-- Rode isso UMA VEZ no banco que você já tem. É seguro rodar mais de uma vez (idempotente).
-- Não apaga nada — só adiciona a coluna de corte. Pra definir a data/capital do reinício,
-- use a tela Parâmetros > Conta > Reiniciar ciclo no app (ou um UPDATE manual, se preferir).

alter table parametros add column if not exists data_inicio_ciclo date;
