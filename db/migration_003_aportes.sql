-- Migração: tabela de aportes (depósitos feitos na conta DEPOIS da abertura).
-- Rode isso UMA VEZ no banco que você já tem. É seguro rodar mais de uma vez (idempotente).
-- Não toca em `parametros.capital_inicial` — aportes ficam em tabela própria de propósito,
-- pra não misturar "ponto de partida da conta" com "dinheiro que entrou depois".

create table if not exists aportes (
    id bigint generated always as identity primary key,
    data date not null,
    valor numeric(12,2) not null,
    observacoes text,
    created_at timestamptz not null default now()
);

create index if not exists idx_aportes_data on aportes (data);

alter table aportes enable row level security;
drop policy if exists "allow all - aportes" on aportes;
create policy "allow all - aportes" on aportes
    for all to anon, authenticated using (true) with check (true);
