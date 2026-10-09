# Cobertura da missão e limites de implementação

Esta entrega é um laboratório funcional com testes, dados e evidência reproduzível. Não é certificação de sistema profissional pronto para operar capital.

|Área|Implementado / executado|Limite explícito|
|---|---|---|
|Baseline|ZIP e hashes, V1 original preservado, auditoria do código|Não isola quantitativamente efeito de cada correção|
|Dados|30 candidatos, 2 anos, 1m original, 5m/15m/1h/4h derivados, Parquet, DuckDB, checksums, UTC, qualidade, retomada|Universo candidato manual; histórico completo de listing/delisting e filtros não adquirido|
|Universo|Elegibilidade e rank por histórico de volume, warmup contínuo; catálogo inclui nomes históricos; removidos/migrados no conjunto|Não elimina seleção inicial nem todos os ativos mortos; bloqueia aprovação|
|Regimes|EMA/slope, ADX, ATR, volatilidade e anomalia, somente passado|Sem HMM; thresholds são hipóteses fixas|
|Padrões|10 famílias formais, sensibilidade, métricas por símbolo/regime e período, resultados negativos preservados|Microestrutura desativada; sem mineração ilimitada de combinações|
|ML|3 modelos, 4 horizontes, 3 janelas sincronizadas, 3 classes, scaler de treino, calibração cronológica, purga/embargo|Amostragem e limite de linhas; sem CV combinatória; rótulo de retorno fixo e barreira separados|
|Estratégias|10 manuais + ML; stops, alvos, trail, tempo e limites; registry com hashes e ativação nula|Família de microestrutura indisponível; não inventada|
|Adaptação|Híbrida por regime causal, registro de versões, bloqueio de promoção|Aprendizado online/adaptive winner e rollback automático não ativados; nenhum candidato elegível|
|Notícias|Interface com publicação/disponibilidade, mocks proibidos na evidência|Feed público histórico confiável não adquirido; efeito incremental não testado|
|Execução|Fila temporal, delay, taxa separada, impacto adverso, participação pelo volume passado, filtros Decimal, parcial/cancelamento, saldo, stop primeiro, gaps|Taker simulado; sem reconstrução de fila maker/order book; filtros atuais como proxies|
|Validação|Descoberta, validação, holdout histórico conhecido, blocos/Bonferroni, random/caixa/BH, stress, sensibilidades|Final prospectivo pendente; PBO/DSR não estimados; IC por subgrupo não usado para aprovação|
|Risco|0,5% individual, 1% agregado, 25% posição, 50% exposição, 2 posições, 20 entradas/dia, diário2%, DD10%, kill|Gaps e latência podem ultrapassar limites; não é perda máxima garantida|
|Paper|Multi-symbol WS, quotes observadas, warmup/reconexão, SQLite/WAL, ids únicos, relógio, logs, scanner, corretor virtual com testes|Nenhuma estratégia aprovada/ativa; não há lucro paper de estratégia; não instala serviço24/7; retenção limitada|
|Dashboard|6 abas, dados medidos, scanner ao vivo, filtros/curvas, journal, kill local|Sem painel de notícia ou depth inexistentes; modelo live não promovido|
|Autonomia|CLI de coleta→integridade→features→hipóteses→ML→backtests→registro→decisão; budgets e checkpoint|Sem compra de serviços, scheduler externo ou ativação de ordens; paper iniciado separadamente por desenho|
|Testes|Regressões de dados/causalidade/sizing/fees/PNL/filters/risk/ML/API/WS local/persistência/recuperação|Testes de mecanismo não equivalem a validação econômica ou endurance24/7|

## Regra de promoção

Mesmo que alguma métrica histórica fique positiva, a ativação permanece bloqueada por universo/filtros históricos incompletos, ausência de final inédito e paper sem amostra validada. `promotion_enabled=false`; não há conexão com ordens reais. A alternativa operacional vigente é caixa/NO_TRADE.

## Custos

Nenhuma API paga, assinatura, hospedagem contratada ou capital de negociação gasto. Downloads, disco, CPU e rede locais têm consumo medido ou limitado. Dependências vêm do registro público PyPI; arquivo lock registra as versões utilizadas.
