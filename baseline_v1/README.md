# Laboratório Quantitativo de Cripto — MVP de paper trading

Este projeto é um laboratório de pesquisa para Binance Spot. Ele baixa somente dados públicos e não implementa envio, assinatura ou cancelamento de ordens. Não precisa de conta nem de chaves. O modo paper grava decisões e execuções simuladas no computador; não movimenta dinheiro.

## Conteúdo

- `quantlab.py`: download, backtest cronológico, métricas, dashboard e paper trading.
- `data/`: candles horários originais da Binance, em CSV, para reproduzir os resultados sem rede.
- `results/`: métricas, operações e curvas de capital geradas pelo backtest.
- `dashboard.html`: visão local dos resultados, sem bibliotecas remotas.
- `research.md`: resumo do protocolo, resultados, limitações e referências.
- `config.json`: parâmetros congelados do experimento.

## Reproduzir

Requer Python 3.10 ou superior, sem pacotes de terceiros.

```powershell
python quantlab.py backtest --data-dir data --out-dir results
python quantlab.py dashboard --results-dir results --output dashboard.html
```

Para baixar novamente os dados públicos e recalcular:

```powershell
python quantlab.py download --start 2021-01-01 --end 2026-10-08 --data-dir data
python quantlab.py backtest --data-dir data --out-dir results
python quantlab.py dashboard --results-dir results --output dashboard.html
```

Datas de fim são exclusivas, em UTC. A origem é `GET https://data-api.binance.vision/api/v3/klines`, sem autenticação. O script remove candles ainda abertos. Os CSV fornecidos incluem a janela fechada disponível quando foram coletados; uma nova coleta pode diferir nas últimas linhas.

## Paper trading

O comando é explicitamente simulado e só usa `GET` público de candles. Inicie uma estratégia por vez:

```powershell
python quantlab.py paper --strategy momentum_pullback --symbol BTCUSDT
```

Interrompa com `Ctrl+C`. `paper/state.json` guarda a carteira virtual e `paper/events.csv` registra sinais, entradas e saídas. A carteira inicia com cerca de 99,76 USDT, equivalente a R$500 na PTAX de referência. Para parar imediatamente, crie `paper/KILL`; o processo verifica o arquivo a cada cinco segundos. O modo é configurado para arriscar no máximo 0,5% do saldo virtual por operação, limitar perda diária a 2% e limitar exposição a 25% por posição. Um erro de rede, candle vencido ou intervalo ausente interrompe novas entradas. Esses limites pertencem à simulação e não protegem uma conta real.

## Aviso

Backtest não é previsão. Os R$500 são convertidos para USDT usando PTAX de venda de referência de 8 out. 2026 (R$5,0119/US$); USDT é aproximado como USD. O cálculo aplica o mínimo de 5 USDT e os passos de lote consultados na Binance, mas não simula o spread da conversão BRL/USDT, depósito, saque ou imposto. Esses valores podem mudar; o PTAX não é cotação executável. O projeto não recomenda investimento nem afirma rentabilidade. Com R$500, taxas e custos de execução podem consumir uma parcela relevante de qualquer ganho.
