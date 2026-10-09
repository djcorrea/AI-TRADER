# Relatório de pesquisa — laboratório quantitativo cripto

**Atualizado:** 8 de outubro de 2026. **Mercado:** Binance Spot, pares USDT. **Modo:** pesquisa histórica e paper trading; não há envio de ordens.

## O que foi medido

Três regras simples, pré-definidas e sem busca de parâmetros, foram comparadas em BTCUSDT, ETHUSDT e SOLUSDT com candles de 1 hora. Os pares estavam em estado `TRADING` na consulta e seus volumes negociados nas últimas 24 horas eram, respectivamente, cerca de US$1,78 bi, US$1,05 bi e US$390 mi. A seleção por liquidez atual não prova que esses mesmos pares seriam os mais líquidos em todo o passado e deixa viés de sobrevivência.

As janelas são cronológicas e não se sobrepõem: desenvolvimento (2021–2023), validação (2024) e teste fora da amostra (2025-01-01 a 2026-10-08 UTC). Cada janela inicia uma conta virtual independente equivalente a R$500. Indicadores usam somente candles já fechados; o sinal é executado na abertura do candle seguinte. Uma lacuna horária bloqueia novos sinais até haver continuidade. Stop e trailing são simulados com candles OHLC, priorizando stop quando mais de uma condição aparece na mesma vela.

As candidatas foram:

- **Momentum com pullback:** EMA50 acima da EMA200; RSI(14) cruza 40 para cima e o fechamento está acima da EMA50. Stop inicial de 2 ATR, trailing de 3 ATR e limite de 72 horas.
- **Rompimento de volatilidade:** fechamento acima da máxima anterior de 20 candles, com ATR(14) entre 0,2% e 5% do preço. Stop de 2 ATR, trailing de 3 ATR e limite de 48 horas.
- **Reversão à média:** fechamento abaixo da banda inferior de Bollinger(20, 2 desvios) e RSI(14) até 30. Saída na média, stop de 2 ATR e limite de 36 horas.

Todas operam somente compradas, com uma posição por par, risco-alvo de 0,5% do patrimônio por operação, posição limitada a 25% do patrimônio e bloqueio de novas entradas após perda diária de 2%. Não há alavancagem, martingale ou grid. O risco simultâneo pode somar até três posições, uma por par.

## Custos e regras da exchange

O modelo cobra 0,10% de comissão por lado, tarifa publicada para o usuário regular no Spot; não pressupõe desconto BNB, nível VIP ou promoção. Acrescenta spread hipotético de 0,05% e slippage hipotético de 0,05% por lado, totalizando 0,20% por lado e 0,40% por ida e volta. Esses dois componentes são hipóteses conservadoras fixas, não cotações históricas de livro.

Os R$500 são convertidos para aproximadamente 99,76 USDT pela PTAX de venda do USD do Banco Central em 8/10/2026 (R$5,0119 por dólar); USDT é aproximado como USD. O dimensionamento arredonda a quantidade para o passo LOT_SIZE registrado e ignora entradas abaixo do mínimo NOTIONAL de 5 USDT. Essa conversão de referência não é uma cotação executável e não contempla spread da conversão para BRL, depósito, saque ou imposto. Reconfira os filtros e a taxa efetiva na sua conta: a Binance pode atualizar parâmetros, e a elegibilidade/rota pode mudar.

O downloader usa somente endpoints públicos `GET`, sem chave. Respeita `Retry-After` e recua em respostas de limite/indisponibilidade; a Binance documenta limites por IP, HTTP 429 e bloqueio 418 em violações repetidas. A coleta encontrou 50.530 candles para cada par, de 2021-01-01 a 2026-10-07 23:00 UTC, com sete intervalos ausentes em cada série. Os hashes SHA-256 dos CSV estão em `results/metrics.json`.

Além do histórico realmente ausente, o estresse de disponibilidade injeta uma falha determinística de seis horas em cada bloco de 30 dias. Durante a falha não há processamento e posições virtuais são liquidadas na primeira abertura observada após a volta do feed. Isso é um cenário hipotético, não uma afirmação sobre indisponibilidade histórica da Binance.

## Resultado fora da amostra

Os números exatos, os resultados das outras janelas, as curvas e todas as operações estão em `results/metrics.json`, `results/*_trades.csv` e `results/*_equity.csv`. A expectativa é o retorno líquido médio por operação sobre o notional executado. O intervalo de 95% foi obtido por 3.000 reamostragens bootstrap de operações individuais (percentis 2,5 e 97,5); ele não corrige autocorrelação, dependência entre moedas, escolha entre estratégias ou incerteza dos custos.

| Candidata | Retorno líquido | Operações | Profit factor líquido | Drawdown máximo | Expectativa/operação (IC 95%) | Estresse de indisponibilidade | Caixa nulo | Buy-and-hold equiponderado |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Momentum com pullback | −0,75% (−R$3,75) | 56 | 0,95 | −4,26% | −0,038% [−0,703%; 0,664%] | +0,01% | 0% | −24,44% |
| Rompimento de volatilidade | −38,61% (−R$193,03) | 759 | 0,75 | −50,41% | −0,311% [−0,523%; −0,079%] | −40,36% | 0% | −24,44% |
| Reversão à média | −47,45% (−R$237,24) | 548 | 0,49 | −47,63% | −0,511% [−0,681%; −0,327%] | −48,36% | 0% | −24,44% |

O benchmark buy-and-hold distribui o capital igualmente entre os três ativos e cobra os mesmos custos de execução nos extremos do período; não estima drawdown intraperíodo. A estratégia nula mantém caixa sem operar e rende 0% no modelo. O estresse tem retorno de +0,01%, −40,36% e −48,36%, respectivamente. O resultado ligeiramente positivo do momentum sob falhas é uma consequência do conjunto específico de trades perdidos, não sinal de vantagem: sua faixa de expectativa continua abrangendo zero.

## Interpretação e limites

Não trate um backtest como previsão ou prova de vantagem. Os critérios foram desenhados para pesquisa, e resultados negativos são evidência contra usar essas regras como estão. No teste, caixa a 0% superou todas as três candidatas; o momentum perdeu menos que buy-and-hold, mas não superou caixa. Mesmo se uma média parecesse positiva, este teste não justificaria arriscar os R$500: a faixa bootstrap supõe operações independentes, o teste entre muitas ideias produz viés de seleção, e o custo real pode ser maior. Com capital pequeno, a comissão, a conversão BRL/USDT e o mínimo do par pesam mais.

OHLC horário não reconstitui fila, profundidade, spread variável, latência real, execução parcial, falha de stop na exchange ou sequência intrabar. O estresse de falha é apenas um cenário. A PTAX não é preço executável de USDT. O modelo não inclui taxas de conversão, depósito/saque, tributos, indisponibilidade da exchange inteira ou dados de universo histórico dos ativos.

O modo paper lê somente candles públicos. Seu stop, limite diário e kill switch são lógica local de simulação; um computador desligado, travamento ou falha de rede pode impedir até a simulação de registrar saídas. Nada nele protege fundos reais.

## Fontes consultadas

- Binance, [tarifas Spot](https://www.binance.com/en/fee/trading): tarifa publicada de usuário regular, VIP e desconto BNB.
- Binance Developers, [REST API Spot — limites e dados públicos](https://developers.binance.com/en/docs/products/spot/rest-api): endpoints, limites por IP, 429 e 418. A documentação recomenda a base `data-api.binance.vision` para dados públicos.
- Binance Developers, [filtros de símbolos](https://developers.binance.com/en/docs/products/spot/filters): regras como LOT_SIZE e NOTIONAL.
- Binance Developers, [dados de mercado Spot](https://developers.binance.com/en/docs/products/spot/market-data-endpoints): candles e informações públicas de mercado.
- Banco Central do Brasil, [API PTAX](https://dadosabertos.bcb.gov.br/dataset/dolar-americano-usd-todos-os-boletins-diarios): cotação USD/BRL de referência usada para converter R$500.
- CVM, [criptoativos e riscos](https://www.gov.br/cvm/pt-br/assuntos/protecao/mercado-forex/criptoativos-forex): alerta sobre características, riscos e ofertas com promessas de rentabilidade extraordinária.
