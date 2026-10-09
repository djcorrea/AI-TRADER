# Auditoria do baseline V1

O código, configuração, dados e resultados originais foram preservados em `../BASELINE_V1.zip`. `BASELINE_V1_manifest.json` contém hashes SHA256 por arquivo. O V1 permanece disponível em `../quant-lab` e não deve ser tomado como sistema aprovado.

## Achados por inspeção do código

1. **Vazamento no dimensionamento:** `backtest_strategy` processava as saídas intrabar e atualizava posições pelo fechamento atual antes de dimensionar entradas na abertura do mesmo candle. Isso disponibilizava patrimônio e recursos futuros. No V2, marcação na abertura, saídas na abertura, compras, saídas intrabar e marcação no fechamento ocorrem nessa ordem.
2. **Alvo de reversão:** a média calculada com o fechamento do próprio candle era confrontada com a máxima daquele candle. No V2, o alvo é congelado com o candle do sinal.
3. **Patrimônio durante bloqueio:** a atualização de preços ficava dentro da condição que liberava entradas. O V2 marca posições ao fechamento mesmo quando bloqueia novas compras; indisponibilidade de execução é separada da trajetória de preços usada na avaliação histórica.
4. **Latência:** o V1 chamava a abertura seguinte ao candle do sinal de “uma barra completa de atraso”. Essa abertura ocorre imediatamente após o fechamento. No V2, latência=1 significa esperar uma barra completa, entrar em i+2 após sinal em i.
5. **Risco agregado:** posições individualmente limitadas podiam somar exposição excessiva. O V2 limita exposição agregada a 50%, risco planejado agregado a 1% e duas posições. Stops e circuit breakers podem sofrer gaps e não garantem perda máxima.
6. **Estatística:** bootstrap V1 assumia negócios independentes, sem correção de seleção. O V2 usa blocos calendários de sete dias, inclui dias sem negócio e reporta intervalos nominais e por família de 120 hipóteses. São estimativas aproximadas, não comprovação de estacionariedade.
7. **Paper:** o V1 não tinha a mesma latência nem persistência operacional completa. V2 usa WebSocket público, armazenamento SQLite com WAL, unicidade de candles, recuperação e circuitos de observação. Nenhuma estratégia tem ativação aprovada.

Os retornos do V1 não são reapresentados como evidência validada. A auditoria identifica mecanismos; não determina quanto cada defeito alterou cada retorno histórico. A comparação quantitativa V1/V2 também muda universo, período e regras, portanto não isola o efeito de uma correção.

## Testes de regressão

`tests/test_lab.py` verifica invariância das features ao truncar/mudar o futuro, purga por fim de rótulo, embargo, atraso de execução, tamanho baseado na abertura, taxas independentes, reconciliação de caixa, dados inválidos, tick/lot/notional, alvo e stop simultâneos, risco, persistência, kill switch, recuperação e indisponibilidade de aprovação.

Testes sintéticos exercitam mecanismos. Não são resultados de mercado nem evidência de lucro.
