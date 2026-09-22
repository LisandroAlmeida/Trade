-- Migração: WIN "hardcoded" -> tabela de ativos (WIN + WDO), cada um com seu
-- próprio valor por ponto / emolumento / margem / stop padrão.
-- Rode isso UMA VEZ no banco que você já criou com o schema.sql anterior (só WIN).
-- É seguro rodar mais de uma vez (idempotente).

create table if not exists ativos (
    codigo text primary key,
    nome text not null,
    valor_por_ponto numeric(10,4) not null,
    emolumento_por_contrato numeric(10,4),
    margem_por_contrato numeric(12,2),
    stop_loss_pontos integer,
    stop_gain_pontos integer,
    habilitado boolean not null default true,
    updated_at timestamptz not null default now()
);

-- Migra os parâmetros do WIN que já estavam em `parametros` para a nova tabela `ativos`,
-- carregando os valores atuais (inclusive o emolumento já calibrado com seus dados reais).
insert into ativos (codigo, nome, valor_por_ponto, emolumento_por_contrato, margem_por_contrato, stop_loss_pontos, stop_gain_pontos)
select
    'WIN',
    'Mini Índice (WIN)',
    coalesce((select valor_por_ponto from parametros where id = 1), 0.20),
    coalesce((select emolumento_por_contrato from parametros where id = 1), 0.50),
    coalesce((select margem_por_contrato from parametros where id = 1), 150.00),
    coalesce((select stop_loss_pontos from parametros where id = 1), 300),
    coalesce((select stop_gain_pontos from parametros where id = 1), 500)
on conflict (codigo) do nothing;

insert into ativos (codigo, nome, valor_por_ponto, emolumento_por_contrato, margem_por_contrato, stop_loss_pontos, stop_gain_pontos)
values ('WDO', 'Mini Dólar (WDO)', 10.00, null, null, null, null)
on conflict (codigo) do nothing;

-- operacoes.ativo (texto livre, ex: 'WINV26') -> operacoes.ativo_codigo (FK para ativos.codigo)
do $$
begin
    if exists (select 1 from information_schema.columns where table_name = 'operacoes' and column_name = 'ativo') then
        alter table operacoes rename column ativo to ativo_codigo;
    end if;
end $$;

alter table operacoes alter column ativo_codigo drop default;
update operacoes set ativo_codigo = 'WIN' where ativo_codigo is null or ativo_codigo not in (select codigo from ativos);

do $$
begin
    if not exists (
        select 1 from pg_constraint where conname = 'operacoes_ativo_codigo_fkey'
    ) then
        alter table operacoes
            add constraint operacoes_ativo_codigo_fkey foreign key (ativo_codigo) references ativos (codigo);
    end if;
end $$;

-- Parâmetros de ativo saem de `parametros` (agora só guarda dados de conta: capital, IRRF, qtd padrão)
alter table parametros drop column if exists margem_por_contrato;
alter table parametros drop column if exists valor_por_ponto;
alter table parametros drop column if exists stop_loss_pontos;
alter table parametros drop column if exists stop_gain_pontos;
alter table parametros drop column if exists emolumento_por_contrato;

create index if not exists idx_operacoes_ativo on operacoes (ativo_codigo);

alter table ativos enable row level security;
drop policy if exists "allow all - ativos" on ativos;
create policy "allow all - ativos" on ativos
    for all to anon, authenticated using (true) with check (true);

create or replace view operacoes_calculadas as
select
    o.*,
    a.nome as ativo_nome,
    coalesce(o.resultado_apos_taxas_real, o.resultado_apos_taxas_estimado) as resultado_apos_taxas_final,
    (o.resultado_apos_taxas_real is not null) as valor_confirmado
from operacoes o
join ativos a on a.codigo = o.ativo_codigo;
