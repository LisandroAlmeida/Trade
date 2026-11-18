-- Migração: suporte a "Mesa" (conta de mesa proprietária/prop firm, ex.: Canário),
-- separada da conta real (BTG/EQI). Regras, custos e ciclo são diferentes da conta
-- principal, então ficam em tabelas próprias em vez de reaproveitar parametros/operacoes.
-- Rode isso UMA VEZ no banco que você já tem. É seguro rodar mais de uma vez (idempotente).

create table if not exists mesa_parametros (
    id smallint primary key default 1,
    conta_numero text,
    metodo text,
    plano text,
    perda_diaria_maxima numeric(12,2),
    perda_total_maxima numeric(12,2),
    repasse_pct numeric(5,4),              -- ex.: 0.95 = 95%
    qtd_contratos_max integer,
    dias_min_operados integer,
    saldo_minimo_saque numeric(12,2),
    taxa_corretagem_contrato numeric(10,4), -- manual — preencha quando souber o valor real da mesa
    ciclo_numero integer,
    ciclo_inicio date,
    ciclo_fim date,
    status_pagamento text,
    status_saque_texto text,                -- texto livre (ex.: "Janela abre em 24 dias")
    stop_diario_pessoal numeric(12,2),       -- sua própria trava de perda diária (decisão sua, só registro)
    updated_at timestamptz not null default now(),
    constraint mesa_parametros_singleton check (id = 1)
);

insert into mesa_parametros (id) values (1) on conflict (id) do nothing;

create table if not exists mesa_resultados (
    id bigint generated always as identity primary key,
    data date not null,
    valor numeric(12,2) not null,   -- resultado líquido do dia na mesa (R$), já considerado pela mesa
    contratos integer,              -- opcional — quantos contratos operou nesse dia
    observacoes text,
    created_at timestamptz not null default now()
);

create index if not exists idx_mesa_resultados_data on mesa_resultados (data);

alter table mesa_parametros enable row level security;
drop policy if exists "allow all - mesa_parametros" on mesa_parametros;
create policy "allow all - mesa_parametros" on mesa_parametros
    for all to anon, authenticated using (true) with check (true);

alter table mesa_resultados enable row level security;
drop policy if exists "allow all - mesa_resultados" on mesa_resultados;
create policy "allow all - mesa_resultados" on mesa_resultados
    for all to anon, authenticated using (true) with check (true);
