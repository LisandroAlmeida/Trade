-- Migração: métricas extra para a Mesa (inspiradas no painel da Canário) —
-- drawdown, % de taxas sobre P&L, operações/dia e quebra de desempenho por ativo (WIN/WDO).
-- Todos os campos novos são opcionais; registros já lançados continuam funcionando normalmente.
-- Rode isso UMA VEZ no banco que você já tem. É seguro rodar mais de uma vez (idempotente).

alter table mesa_resultados add column if not exists ativo_codigo text;    -- 'WIN' | 'WDO' | 'WIN+WDO' (opcional)
alter table mesa_resultados add column if not exists operacoes integer;   -- nº de operações/trades no dia (opcional)
alter table mesa_resultados add column if not exists taxas numeric(12,2); -- total de taxas pagas no dia, R$ (opcional — só referência, valor já é líquido)
