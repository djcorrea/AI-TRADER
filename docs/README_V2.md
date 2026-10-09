# QUANT AI V2 — laboratório local de criptomoedas

**Somente dados públicos, backtest e simulação. Sem chaves, conta conectada ou ordens reais. Capital virtual R$500. Nenhuma estratégia aprovada.**

## Abrir

O painel local fica em http://127.0.0.1:4174 quando o servidor estiver rodando. Abas: visão geral, scanner, modelos de IA, backtesting, paper e laboratório. Clique uma linha de experimento para ver o patrimônio.

Na pasta deste projeto, PowerShell:

```powershell
python -m venv .venv
& .venv/Scripts/python.exe -m pip install -r requirements-lock.txt
& .venv/Scripts/python.exe -X utf8 run.py serve
```

Em outro terminal:

```powershell
& .venv/Scripts/python.exe -X utf8 run.py paper
```

O processo permanece ligado até ser encerrado; computador, rede e processo precisam permanecer ativos. Não foi instalado serviço de inicialização. `--duration 120` limita a observação a 120 segundos. O botão **Parar paper trading** persiste o bloqueio de compras simuladas; posições virtuais só podem ser encerradas com cotação fresca. O botão não desliga a captura pública. Não há botão de operação real.

## Reproduzir pesquisa

```powershell
& .venv/Scripts/python.exe -X utf8 run.py data
& .venv/Scripts/python.exe -X utf8 run.py research
& .venv/Scripts/python.exe -X utf8 recompute_metrics.py
& .venv/Scripts/python.exe -X utf8 annotate_models.py
& .venv/Scripts/python.exe -X utf8 audit_data.py
& .venv/Scripts/python.exe -X utf8 audit_results.py
& .venv/Scripts/python.exe -X utf8 build_report.py
& .venv/Scripts/python.exe -m pytest -q --basetemp .pytest-work --junitxml reports/tests.xml
```

Downloads são retomados pelas partições verificadas. `research --resume` retoma experimentos salvos quando os hashes de configuração e mecanismos causais coincidem; mudanças exigem nova execução. `data` consulta catálogo de símbolos históricos, verifica checksums oficiais, coleta 1m mensal e deriva 5m/15m/1h/4h somente com barras completas. `data/lab.duckdb` expõe uma view dos arquivos 15m. Datas em UTC, timestamps normalizados de microsegundos/milissegundos para ms. Meses sem arquivo constam no manifesto, não são preenchidos.

O ambiente desta entrega já foi instalado em `../../work/venv` com Python 3.13.5 no Windows; os comandos acima criam um ambiente independente para uso futuro. O ZIP portátil inclui fonte, modelos, evidências, documentação e baseline V1. O cache público de aproximadamente 3,4 GB e o banco de paper permanecem na pasta local e são recriáveis pelos comandos de coleta.

## Limites registrados antes da pesquisa

- 30 candidatos históricos, 2024-01-01 até 2026-01-01 exclusivo. Universo elegível: 30 dias contínuos, volume médio diário passado >=10 milhões USDT, até 20 candidatos por liquidez. Há candidatos removidos/migrados; catálogo e universo candidato são distintos. **Universo manual ainda tem viés de seleção.**
- Downloads: quatro conexões, 2,5 GB de arquivos novos por execução, 8 GB de dados persistidos, 30 minutos. Arquivos mensais comprimidos e Parquet locais; sem serviço pago.
- Máximo 120 experimentos, 30 minutos de pesquisa estratégica antes dos modelos; modelos também limitados a 30 minutos, 80 mil linhas de ajuste, 20 mil linhas de avaliação por janela. A RAM é reduzida por processamento por ativo e amostragem, mas não há limitador de RAM do sistema operacional.
- 10 famílias manuais, variantes .9/1/1.1 somente em descoberta, especificação principal fixa 1. Microestrutura desativada por ausência de livro histórico. Híbrida por regime é uma hipótese fixa; seleção adaptativa de vencedores continua bloqueada.
- ML: regressão logística com regularização, random forest, LightGBM, horizontes 5/15/30/60 minutos, features causais, scaler ajustado no treino, calibração multinomial em cauda cronológica do treino, purga e embargo por horizonte. Probabilidades de ganho líquido positivo, negativo e sem oportunidade; rótulos de primeira barreira preservados separadamente. Não implementa CV combinatória. EV usa payoffs condicionais já líquidos, sem subtrair taxas outra vez.
- Notícias: interface causal com timestamps e mocks de teste; feed e uso em modelos desativados. Não há dados protegidos ou APIs pagas.

## Execução e custos

Backtest comprado Spot: sinal após candle fechado; uma barra completa de espera; entrada na abertura posterior, preço com spread/slippage adversos e comissão separada. Posição dimensionada sem preço futuro e limitada pelo volume **passado**. Barreira stop ganha quando stop e alvo aparecem no mesmo OHLC; ambiguidade registrada. Média alvo fixa no sinal; trail atualizado ao fechamento para a próxima barra. Ausência de cotação é tratada com haircut de recuperação zero, explicitamente hipotético, sem venda fictícia no último preço.

Comissão base 0,10%/lado; meio spread 0,05%/lado; slippage 0,05%/lado: aproximadamente 0,4% ida e volta, sem desconto BNB. Stress caro: 0,15% comissão + 0,10% spread + 0,10% slippage por lado, preenchimento 50%. Stress de disponibilidade: 6h/30 dias, latência 2 barras. Não reproduz fila maker nem profundidade histórica. Preenchimentos parciais são hipóteses de cenário, nunca execuções reais observadas.

Filtros PRICE_FILTER, LOT_SIZE, MARKET_LOT_SIZE, MIN_NOTIONAL e NOTIONAL são aplicados com Decimal e snapshot atual quando disponível. Onde faltam, são proxies assumidos e marcados. Snapshot atual não é histórico e bloqueia promoção. A implementação usa execução agressora simulada; não presume maker barato sem evidência.

Risco planejado: 0,5% por entrada, 25% por posição, 50% agregado, 1% de risco agregado, duas posições, 20 entradas/dia; bloqueio diário 2% e cumulativo a partir de drawdown 10%. Saída de risco após fechamento acontece na próxima abertura, portanto gaps podem ultrapassar esses limites. Limite de drawdown não é garantia.

BRL é escala usando PTAX USD venda 5,0119 de 2026-10-08 e USDT≈USD; sem custo de conversão, variação cambial, impostos ou hospedagem. Não representa R$ executáveis na Binance.

## Evidência e aprovação

`results/experiments.json`: todos os experimentos, negativos incluídos; trades e curvas completos em Parquet. `results/models.json`: testes preditivos, Brier, baseline constante, calibração e rótulos; **retorno médio de rótulos sobrepostos não é retorno de carteira**. `models/registry.json`: versões, hashes, treino, métricas, ativação nula. `results/report.json`: cobertura, períodos, hipóteses e limitações.

Descoberta mar–dez/2024; validação jan–jun/2025; holdout retrospectivo jul–dez/2025. Todo esse histórico já esteve acessível no V1, inclusive BTC/ETH/SOL. **O holdout não é um final inédito.** Final realmente prospectivo começa depois do congelamento registrado e ainda precisa de observações novas.

Critério conservador: >=100 negócios, lucro líquido positivo, limite inferior corrigido positivo, PF>=1,3, drawdown aceitável e superar caixa e buy-and-hold. Além disso, estabilidade e stress, integridade e execução devem ser comprovados. Resultados sem amostra são INCONCLUSIVO; negativos REJEITADA; falha de integridade deve invalidar o teste. Mesmo um candidato retrospectivo não é aprovado com os bloqueios atuais.

Buy-and-hold compra até três candidatos mais líquidos elegíveis no começo do período, pesos iguais e sobra de caixa conforme filtros. Tem exposição maior que as estratégias: comparação contextual. Três controles aleatórios pré-fixados usam mesmas regras de execução/risco, frequência ex ante 1%; não são pareamento exato de exposição/turnover. Caixa rende 0% nesta simulação.

Paper captura BTC/ETH/SOL, bookTicker e candles públicos, registra recebimento, conectividade, scanners e decisões NO_TRADE. SQLite/WAL, ids únicos, warmup REST após reconexão, correção de relógio por midpoint, cotação vencida, spread/divergência/liquidez, kill e limites de risco. Fills virtuais e seu saldo são persistidos na mesma transação. O corretor virtual tem entradas/saídas testadas em fixtures; **não ativa estratégia reprovada para fabricar negócios ao vivo**. Retenção bruta limitada a 100 mil eventos; candles fechados, scanner e estimativas ficam por 90 dias, enquanto o diário de fills não é apagado por essa retenção. Não equivale a arquivo integral eterno. Alertas são logs/painel locais. Não envia mensagens a terceiros.

O scanner também calcula estimativas de três classes do modelo previamente fixado `logistic_60m_fold2`, quando as três moedas têm candles fechados sincronizados. O artefato é verificado pelo hash. Esse modelo foi treinado antes de julho de 2025 e permanece **antigo, inativo e não aprovado**. Sua expectativa é uma estimativa baseada no treino; não é lucro observado. O caminho de inferência não tem método para enviar ordens.

## Arquivos

- `lab/`: dados, features/regimes, estratégias, modelos, execução/risco/backtest, estatística, orchestrator, paper, API, interface de notícias.
- `dashboard/`: painel integrado local; `tests/`: regressões; `reports/`: auditoria, testes e relatório quantitativo.
- `data/`: catálogo, snapshots, arquivos originais, Parquet, qualidade e DuckDB.
- `../BASELINE_V1.zip`: baseline original preservado, com manifesto nesta pasta.

Consulte `reports/AUDITORIA_V1.md`, `reports/RESULTADOS.md` e `reports/COBERTURA.md` antes de interpretar uma cifra como evidência.

## Fontes primárias consultadas

- [Arquivos públicos e timestamps Binance](https://github.com/binance/binance-public-data/blob/master/README.md)
- [API pública de dados](https://github.com/binance/binance-spot-api-docs/blob/master/faqs/market_data_only.md)
- [Filtros Spot](https://github.com/binance/binance-spot-api-docs/blob/master/filters.md)
- [WebSocket público e limites](https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md)
- [REST e rate limits](https://developers.binance.com/en/docs/products/spot/rest-api)
- [Tabela de taxas](https://www.binance.com/en/fee/trading)
- [PTAX Banco Central](https://dadosabertos.bcb.gov.br/dataset/dolar-americano-usd-todos-os-boletins-diarios)
