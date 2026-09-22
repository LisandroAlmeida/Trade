-- Schema do app de controle de day trade (WIN + WDO)
-- Espelha a lógica da planilha original "controle_daytrade_win", com duas melhorias:
--  1. separa o valor ESTIMADO (calculado na hora) do valor REAL (confirmado depois,
--     quando a corretora libera o extrato, normalmente no dia seguinte);
--  2. cada ativo (WIN, WDO, ...) tem seu próprio valor por ponto, emolumento, margem
--     e stop padrão — em vez de um único conjunto de parâmetros "global".
--
-- Use este arquivo para um projeto Supabase NOVO (do zero). Se você já tem o banco
-- criado a partir da versão anterior (só WIN), use db/migration_002_ativos.sql.

create table if not exists parametros (
    id smallint primary key default 1,
    capital_inicial numeric(12,2) not null default 983.37,
    aliquota_irrf numeric(5,4) not null default 0.01, -- 1% = 0.01, mesma alíquota p/ qualquer ativo
    qtd_contratos_padrao integer not null default 1,
    updated_at timestamptz not null default now(),
    constraint parametros_singleton check (id = 1)
);

insert into parametros (id) values (1) on conflict (id) do nothing;

create table if not exists ativos (
    codigo text primary key,               -- 'WIN', 'WDO', ...
    nome text not null,                    -- 'Mini Índice (WIN)', 'Mini Dólar (WDO)'
    valor_por_ponto numeric(10,4) not null,      -- especificação fixa do contrato (B3)
    emolumento_por_contrato numeric(10,4),       -- estimativa calibrada com dados reais (pode ficar em branco até calibrar)
    margem_por_contrato numeric(12,2),           -- exigida pela corretora — varia e deve ser conferida periodicamente
    stop_loss_pontos integer,
    stop_gain_pontos integer,
    habilitado boolean not null default true,    -- aparece no dropdown de lançamento?
    updated_at timestamptz not null default now()
);

insert into ativos (codigo, nome, valor_por_ponto, emolumento_por_contrato, margem_por_contrato, stop_loss_pontos, stop_gain_pontos)
values
    ('WIN', 'Mini Índice (WIN)', 0.20, 0.50, 150.00, 300, 500),
    ('WDO', 'Mini Dólar (WDO)', 10.00, null, null, null, null)
on conflict (codigo) do nothing;

create table if not exists operacoes (
    id bigint generated always as identity primary key,
    data date not null,
    ativo_codigo text not null references ativos (codigo),
    contratos integer not null default 1,             -- contratos por operação (padrão)
    resultado_pontos numeric(10,2),                    -- resultado do dia, em pontos
    resultado_realizado numeric(12,2),                  -- = resultado_pontos * valor_por_ponto(ativo) * contratos (bruto, sem taxas)
    contratos_operados integer,                         -- total de contratos negociados no dia (para estimar emolumento)
    resultado_apos_taxas_estimado numeric(12,2),         -- calculado automaticamente (emolumento + IRRF)
    resultado_apos_taxas_real numeric(12,2),             -- preenchido manualmente quando a corretora confirma (T+1)
    motivo_saida text,                                   -- 'Stop Gain' | 'Stop Loss' | 'Saída manual' | 'Outro'
    observacoes text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_operacoes_data on operacoes (data);
create index if not exists idx_operacoes_ativo on operacoes (ativo_codigo);

-- App sem login por usuário (mesma decisão do app de finanças): mantemos RLS ligado
-- (recomendação do Supabase) mas liberamos leitura/escrita total pra quem tiver a chave anon.
alter table parametros enable row level security;
alter table ativos enable row level security;
alter table operacoes enable row level security;

drop policy if exists "allow all - parametros" on parametros;
create policy "allow all - parametros" on parametros
    for all to anon, authenticated using (true) with check (true);

drop policy if exists "allow all - ativos" on ativos;
create policy "allow all - ativos" on ativos
    for all to anon, authenticated using (true) with check (true);

drop policy if exists "allow all - operacoes" on operacoes;
create policy "allow all - operacoes" on operacoes
    for all to anon, authenticated using (true) with check (true);

-- resultado_apos_taxas_final: usa o valor real quando existir, senão a estimativa.
-- É esse campo que alimenta saldo acumulado, sequências e o resumo.
create or replace view operacoes_calculadas as
select
    o.*,
    a.nome as ativo_nome,
    coalesce(o.resultado_apos_taxas_real, o.resultado_apos_taxas_estimado) as resultado_apos_taxas_final,
    (o.resultado_apos_taxas_real is not null) as valor_confirmado
from operacoes o
join ativos a on a.codigo = o.ativo_codigo;
