# QUANT AI V2 — AI-TRADER

V2 existente migrado para continuidade no Codex Cloud. Dados públicos Binance Spot,
scanner, dashboard e paper trading. Sem chaves, ordens reais ou gasto do capital.
Nenhuma estratégia aprovada. Esta migração não implementa V3.

## Instalar e testar

Python 3.13. Linux/macOS:

```sh
git clone https://github.com/djcorrea/AI-TRADER.git
cd AI-TRADER
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pytest -q
```

Windows: `.venv\Scripts\Activate.ps1`. O lock preserva versões usadas no V2.
Carregue modelos joblib somente de origem confiável; hashes estão no registro.

## Scanner, paper trading e dashboard

```sh
python run.py paper                # scanner público + paper no mesmo coletor
python run.py paper --duration 60  # observação por 60 segundos
python run.py serve --host 127.0.0.1 --port 4174
```

Abra http://127.0.0.1:4174 . Consulte `/api/paper` para disponibilidade/heartbeat.
Scanner BTCUSDT, ETHUSDT, SOLUSDT. Modelos permanecem inativos para operar;
inferência é shadow. Limites existentes: risco 0,5%/operação, perda diária 2%,
drawdown 10%, duas posições, kill switch. Taxa simulada 0,1%/lado, spread/slippage
conservadores, latência e indisponibilidade são modelados. Não há promessa de lucro.

## Nuvem

```sh
HOST=0.0.0.0 PORT=8080 STATE_DIR=/state python run.py cloud
```

`/state` deve ser um volume persistente. API e coletor são processos supervisionados
no mesmo serviço, compartilhando SQLite localmente. PORT/HOST vêm do ambiente;
CLI tem precedência. Uma única instância. `/health` verifica API, não saúde do feed.
Treinamento e aquisição histórica não são iniciados pelo serviço contínuo.

Componentes individuais, somente com o mesmo volume local:

```sh
STATE_DIR=/state python run.py paper
STATE_DIR=/state HOST=0.0.0.0 PORT=8080 python run.py serve
```

```sh
docker build -t quant-v2 .
docker volume create quant-state
docker run --rm -p 8080:8080 -e PORT=8080 -v quant-state:/state quant-v2
```

Railway: Dockerfile e `railway.toml`; iniciar `python run.py cloud`, montar `/state`,
definir HOST/STATE_DIR e deixar PORT fornecida pela plataforma. Kill remoto desabilitado.
Veja [configuração e pendências](docs/CLOUD_HANDOFF.md). Nenhum deploy pago iniciado.

## Reconstruir dados — job de pesquisa separado

Preserve os resultados antes de recalcular. Não rode no serviço contínuo:

```sh
python run.py data
# Repetir data até completar o manifesto, respeitando o orçamento por execução.
python run.py aggregate
python audit_data.py
python run.py research --resume
python audit_results.py
```

Candles não estão no Git ou imagem. Fontes públicas com SHA256:
[Binance Public Data](https://github.com/binance/binance-public-data),
[arquivos mensais](https://data.binance.vision/), API https://data-api.binance.vision/ .
Config define datas/pares/seeds/orçamentos; `data/download_manifest.json` preserva hashes.
Download verifica arquivos existentes, respeita Retry-After, limita novos downloads a
2,5 GB/execução e dados locais a 8 GB. Arquivos indisponíveis são registrados.
Reprodução depende da disponibilidade/integridade da fonte. Testes unitários não
substituem auditoria dos candles reconstruídos. Checkpoint antigo foi excluído.

## Evidências e continuidade

29.814.300 candles pesquisados localmente, 80 backtests (44 rejeitados, 36 inconclusivos),
36 ajustes de modelos. Nenhuma estratégia aprovada. Resultados anteriores não foram
recalculados nesta migração. O holdout histórico já foi observado.

- [Resultados, métricas e limites](reports/RESULTADOS.md)
- [Documentação V2 anterior](docs/README_V2.md)
- [Continuidade, persistência e pendências Railway](docs/CLOUD_HANDOFF.md)
- [Exclusões](docs/MIGRATION_EXCLUSIONS.md)
- `lab/`: código; `dashboard/`: interface; `tests/`: testes; `models/`: modelos e
  previsões; `results/`: trades/equity/métricas; `research/`: registro de estratégias.

Originais, candles, bancos e logs continuam locais. Baseline V1 publica fontes e
hashes; teste de preservação verifica esses fontes, sem seus datasets.
