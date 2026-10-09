# Exclusões

Preservados localmente; nenhum arquivo original foi removido:

- `data/archives/**`, `data/parquet/**`, `data/derived/**`: históricos brutos/agregados.
- `data/lab.duckdb`, `paper/**`: bancos e estado operacional local.
- `research/checkpoint.json`, `research-run.log`: cache/log ligado ao código anterior.
- `__pycache__/**`, `.pytest_cache/**`, ambientes, bytecode e temporários.
- `reports/tests.xml`, `reports/portable-tests.xml`: paths privados da máquina.
- `reports/paper_before_restart.json`, `reports/paper_observation_snapshot.json`.
- `reports/source_manifest.json`: manifesto antigo, preservado localmente.
- ZIPs de distribuição/baseline integral; baseline V1 publica apenas fontes e hashes.
- `.env`, credenciais, tokens, chaves: não encontrados na seleção; padrões ignorados.

Modelos, previsões, trades e equity Parquet foram incluídos como evidências compactas;
não são os 29,8 milhões de candles. A imagem omite Parquet de resultados/previsões,
testes, relatórios e baseline. O manifesto exato de 2.206 exclusões do V2 está salvo
localmente em `outputs/migration-exclusions.json`.
