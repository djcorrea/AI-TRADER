# AUDITORIA V2 — retomada na nuvem

Status: **AUDITORIA PARCIAL**. A contabilidade dos artefatos foi conferida; os candles originais ainda não foram reconstruídos na nuvem. Não há estratégia aprovada nem evidência nova de rentabilidade.

Baseline recuperado: `d987229e25f8cf69391c33bc5ba8b77dbe386d58`, branch `main`. O Git preserva essa versão; também foi criado um arquivo completo antes das alterações em `/workspace/onboarding/AI-TRADER-V2-d987229.tar`. Fontes V1, configurações congeladas, modelos, previsões, trades e curvas da V2 permanecem preservados.

## CONFIRMADO

Os 63 testes recebidos passaram em Linux/Python 3.13 com `requirements-lock.txt`. A auditoria independente foi reexecutada sobre os arquivos migrados; 80 backtests e 36 versões de modelos reconciliaram saldo final, taxas, lucro líquido, profit factor, drawdown, Brier, quantidade de candidatos e hashes dos modelos. Isso confirma consistência dos artefatos armazenados, sem comprovar fills históricos ou lucro futuro.

Classificações anteriores: 44 rejeitadas e 36 inconclusivas. Nenhuma ativação de modelo. Dos 76 backtests manuais/aleatórios, 69 registraram bloqueio permanente de risco; 75 encerraram seu último negócio pelo menos um dia antes do fim nominal do período. O maior drawdown registrado foi aproximadamente -10,43%. Houve 3.871 saídas por stop, 1.806 por alvo, 2.307 por tempo, 227 por recuperação e cinco por risco na abertura.

As 36 avaliações de ML melhoraram o Brier versus a constante. Somadas, produziram 25 candidatos preditivos; nenhuma produziu candidato no holdout retrospectivo. A proporção da classe positiva variou de 0,715% a 15,425%. Os quatro backtests ML tiveram zero negócios; isso não demonstra lucro nem aprovação.

## BUG ENCONTRADO

1. **Cache sem reconferência de integridade:** `acquire()` retornava metadados `OK` quando Parquet e JSON existiam, sem conferir seus bytes ou o ZIP. Um teste alterando o hash esperado reproduziu a aceitação indevida.
2. **Horizonte dos rótulos atravessava lacunas:** deslocamentos por número de linhas eram interpretados como minutos. Um candle ausente deslocava a saída para outro tempo, mantendo o label válido. O erro foi reproduzido com um minuto removido.
3. **Features atravessavam lacunas:** médias e retornos poderiam combinar barras separadas por intervalos maiores que o declarado. Isso não é uso de futuro, mas viola a definição temporal da feature.
4. **Calibração com classe ausente:** somente o classificador tinha suas três classes verificadas. Um calibrador com duas classes podia ser aceito, apesar de inferência/EV esperarem três colunas. A ausência da classe positiva foi reproduzida.
5. **Validação incompleta de valores finitos:** NaN em `n`, `tbv` ou `tbqv` passava. Três testes reproduziram o problema; timestamps também passaram a integrar a verificação.
6. **Interseção de lotes:** arredondar por dois grids sucessivos não garante ambos. Exemplo: 0,20 → 0,18 no grid 0,03 → 0,16 no grid 0,04; 0,16 viola o grid 0,03. O grid comum deve ser 0,12 nesse caso.
7. **Exportação portátil ampla:** o ZIP percorria toda a árvore e não excluía `.venv`, `.git` e `.env`. O filtro de exportação não era equivalente ao `.gitignore`. Não foi encontrada exposição efetiva de segredo nos artefatos recebidos; o defeito foi reproduzido com arquivos de fixture.
8. **Relatório usava estado incorreto na nuvem:** o snapshot paper do gerador de relatório ignorava `STATE_DIR` e lia/criava o banco no checkout.

## CORREÇÃO EXECUTADA

- Reconfere hashes do Parquet e ZIP e valida candles antes de reutilizar o cache. Arquivos suspeitos são mantidos para diagnóstico e classificados `ERROR`.
- Invalida labels cuja janela inteira, incluindo a latência, não seja contínua. Labels e resultados indisponíveis ficam ausentes, sem virar classe neutra.
- Reinicia o cálculo das features após cada lacuna e exige novo warmup.
- Exige as três classes também na calibração cronológica.
- Verifica finitude de todos os campos numéricos do candle.
- Dimensiona quantidades em um grid que satisfaz os dois filtros simultaneamente, usando Decimal e mínimo múltiplo comum.
- Exporta apenas caminhos e tipos de artefatos selecionados; exclui runtime, credenciais, Git e links externos. Preserva fontes V1 publicadas.
- Usa `state_path()` no snapshot de relatório; mantém fills persistidos atomicamente e estende a retenção temporal aos eventos operacionais, preservando o diário de fills.

Testes de regressão foram adicionados. As correções não foram usadas para recalcular nem substituir os resultados históricos da V2. Seus impactos financeiros ainda não foram medidos.

## LIMITAÇÃO

| Item da missão | Verificação nesta etapa | Limite |
|---|---|---|
| Procedência dos candles | Manifestos e hashes anteriores presentes | ZIPs e candles foram excluídos da migração; validação dos bytes pendente |
| Disponibilidade e look-ahead | Inspeção da ordem de eventos e testes de causalidade/latência | Não reexecutado sobre o histórico original |
| Saldo, PnL, taxas, PF e DD | Reconciliação independente dos 80 artefatos | Coerência contábil não prova preços negociáveis |
| Tamanho e exposição | Tests de sizing, risco agregado e uso de volume passado | Exposição conjunta histórica precisa de replay com candles |
| Stops, alvos e slippage | Ordem temporal, stop adverso em empate, saída na abertura e cenários conferidos | Intrabar e profundidade não observados; gaps podem superar limite de risco |
| Fills parciais e ordens | Hipóteses de execução e transação atômica testadas | Sem fila maker ou fills históricos observados |
| Seleção temporal de ativos | Elegibilidade usa histórico passado; scanner usa listing atual | Universo manual e filtros atuais não eliminam viés de seleção |
| Regimes | Features causais e reset de lacunas testados | Limiares são hipóteses fixas, não classes econômicas comprovadas |
| ML e calibração | Probabilidades, scaler, purga/embargo, métricas e hashes verificados | Modelo live antigo, sem aprovação; rótulo e payoff do backtest são diferentes |
| Aprovação e rejeição | Gates, registros inativos e `NO_TRADE` conferidos | Critérios não autorizam dinheiro real; observação prospectiva pendente |

Os metadados da V2 reportam zero lacunas em BTC/ETH/SOL. Portanto os defeitos de lacunas não podem ser atribuídos aos maus resultados antigos sem reconstruir o dataset. A integridade dos novos testes é diferente da integridade dos dados de mercado.

A taxa base de 0,1% por lado é uma hipótese preservada, não a taxa verificada de uma conta atual. Aproximadamente 0,4% de movimento bruto é necessário para compensar a hipótese taker de ida e volta. Maker pode reduzir fricção, mas a fila e os fills continuam desconhecidos; os cenários novos estão identificados como hipóteses.

`PaperBroker.submit()` preenche imediatamente uma cotação fresca quando chamado com aprovação explícita; não implementa a fila de latência do backtest. O coletor atual não chama esse método para modelos inativos. A ativação de um futuro candidato paper precisa implementar e validar essa fila e a autorização pelo protocolo, em vez de tratar o booleano de uma fixture como aprovação de modelo.

Os orçamentos de aquisição/research da V2 são verificações na aplicação, não quotas rígidas do sistema operacional. Em particular, reservas dos downloads concorrentes e estimativas de disco precisam ser acompanhadas: não se deve interpretar os limites como garantia exata de consumo. O módulo de mapa limita linhas e verifica tempo entre ativos; uma análise em andamento pode ultrapassar esse tempo nominal.

## HIPÓTESE

**Drawdowns próximos de -10%:** o bloqueio permanente explica o agrupamento e a interrupção precoce. A ordem de marcação/guarda e os gaps/custos de liquidação explicam pequenas ultrapassagens. Os artefatos reconciliam, mas isso não isola a contribuição da estratégia, da exposição e de cada custo. Não foram removidos os controles de risco para obter mais negócios.

**Poucos candidatos ML:** classe positiva rara, limiar `p > 0,55` e EV líquido `> 0,2%` tornam a seleção restrita. A melhora de Brier pode decorrer principalmente das classes frequentes sem selecionar ganhos suficientemente grandes para os custos. Isso não justifica baixar os limiares após observar o holdout.

**Brier sem lucro:** calibração e previsão são propriedades diferentes da expectativa de uma operação executável. Os rótulos se sobrepõem, a amostra efetiva é menor que a quantidade de linhas e os resultados não equivalem a uma carteira. Os dados atuais permitem esse diagnóstico; não demonstram uma vantagem líquida.

## PENDENTE

1. Aplicar a política de rede salva, reconstruir candles e comparar hashes com o manifesto original do commit baseline antes de declarar a V2 reproduzida.
2. Completar históricos recentes e catálogo de listing/delisting/migrações; registrar filtros históricos quando disponíveis e cenários conservadores onde faltarem.
3. Reexecutar casos e pesquisas com as correções, preservando os arquivos originais e registrando o novo fingerprint. Treinamento novo permanece pendente de qualificação dos dados.
4. Produzir o mapa com dados reais. O módulo, endpoint e painel estão implementados e testados com fixtures; o painel retorna `UNAVAILABLE` neste ambiente.
5. Executar as hipóteses predefinidas em `research/protocol_v3.json`, avaliações temporais e ML incremental. Nenhuma pesquisa nova foi apresentada como concluída.
6. Validar feed público real de todos os pares listados. O teste de 30 pares usa um servidor WebSocket local controlado e não comprova acesso à Binance na região Railway.
7. Autenticar Railway e usar projeto/serviço existente com volume `/state`; custos adicionais continuam sem autorização, conforme a missão de não contratar serviços pagos.
8. Obter amostra prospectiva suficiente. Manter shadow separado de paper; modelos inativos e nenhuma ordem real.

## Evidência reproduzível

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -m pytest -q
.venv/bin/python run.py audit
STATE_DIR=/workspace/onboarding/runtime .venv/bin/python run.py cloud --host 127.0.0.1 --port 4174
```

`run.py audit` grava `reports/v3_audit.json`, com hashes das fontes e resultados da reconciliação. A execução atual não alterou `results/`, modelos ou fontes V1. XMLs de testes, verificação HTTP e logs de build estão em `/workspace/onboarding/`.

A V3 não está tecnicamente concluída. O resultado desta etapa é a retomada do desenvolvimento, correções de integridade e ferramentas de diagnóstico verificadas, com blockers explícitos para pesquisa, feed e deployment.
