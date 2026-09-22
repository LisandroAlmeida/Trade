# Trade WIN — Controle de Day Trade

App em Streamlit que substitui a planilha `controle_daytrade_win`: lança operações (WIN ou WDO),
calcula automaticamente o resultado após emolumentos + IRRF, acompanha saldo acumulado, sequências
de gain/loss e um resumo de desempenho.

## Estrutura

- `app.py` — Dashboard (página inicial)
- `pages/1_Lançar_Operação.py` — formulário de lançamento (com dropdown de ativo) + confirmação do valor real (T+1)
- `pages/2_Resumo.py` — resumo agregado + registro completo (com exportação CSV)
- `pages/3_Parâmetros.py` — parâmetros da conta e de cada ativo (capital, IRRF, valor por ponto, emolumento, margem, stop)
- `lib/calculations.py` — todas as regras de cálculo (testadas contra os valores reais da planilha)
- `lib/db.py` — acesso ao Supabase
- `lib/ui.py` — estilo visual compartilhado (tema, formatação R$/%, cabeçalhos)
- `db/schema.sql` — schema completo (projeto Supabase novo, do zero)
- `db/migration_002_ativos.sql` — migração pra quem já tinha o banco da versão anterior (só WIN)

## Multi-ativo (WIN / WDO)

Cada ativo tem seu próprio valor por ponto (especificação fixa da B3 — WIN R$0,20, WDO R$10,00),
emolumento estimado, margem exigida pela corretora e stop padrão, guardados na tabela `ativos`.
O WDO já vem com o valor por ponto certo, mas emolumento/margem/stop ficam em branco até você
preencher em **Parâmetros → Ativos** (dependem da sua corretora e da sua gestão de risco — o app
não inventa esses números).

## Por que separa valor "estimado" de valor "real"

O extrato da corretora só libera o resultado líquido do dia seguinte. Por isso cada operação tem:

- `resultado_apos_taxas_estimado`: calculado na hora, assim que você lança a operação (emolumento
  estimado por contrato + 1% de IRRF sobre o ganho líquido do dia).
- `resultado_apos_taxas_real`: você preenche depois, quando a corretora confirma. A partir daí, o
  app usa sempre o valor real (nunca sobrescreve um valor confirmado com uma nova estimativa).

## Rodando localmente

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # preencha com os dados do seu Supabase
streamlit run app.py
```

## Deploy

1. Crie um projeto gratuito em https://supabase.com, abra o **SQL Editor** e rode o conteúdo de `db/schema.sql` (projeto novo) ou `db/migration_002_ativos.sql` (se já tinha o banco da versão anterior).
2. Pegue a **Project URL** e a **anon key** em Project Settings → API.
3. Suba este repositório no GitHub.
4. Em https://share.streamlit.io, crie um novo app apontando para este repo / `app.py`.
5. Em **Settings → Secrets** do app no Streamlit Cloud, cole:
   ```toml
   supabase_url = "..."
   supabase_key = "..."
   ```
