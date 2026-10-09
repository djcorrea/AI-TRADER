# Continuidade V2 → nuvem

Esta migração preserva o V2. Não implementa V3 nem habilita negociação real.
O código original e os dados brutos continuam no computador de origem.

## O que foi preservado

- Fonte, dashboard, 36 modelos joblib com registro e hashes, previsões Parquet.
- 80 backtests com trades/equity, resultados, relatórios, parâmetros e auditorias.
- Catálogo, checksum dos downloads, qualidade e snapshot público de filtros.
- Código V1 em `baseline_v1/`, manifesto completo V1 na raiz. O teste do baseline
  verifica somente fontes presentes no Git; o arquivo integral com dados permanece local.
- `docs/README_V2.md` é a documentação anterior. Seus comandos locais e referências
  a ZIP/serviços já iniciados descrevem a entrega anterior, não este deploy.

## Resultados anteriores, não recalculados na migração

29.814.300 candles de 1 minuto; 80 backtests (44 rejeitados, 36 inconclusivos),
36 ajustes de modelos. Nenhuma estratégia aprovada. Modelos permanecem inativos;
o scanner usa inferência de observação, sem aprovação automática ou ordens reais.
O período final histórico já foi observado; não é uma nova amostra intocada.
Veja `reports/RESULTADOS.md`, `results/report.json` e os artefatos auditáveis.
Não existe evidência de rentabilidade garantida ou de vantagem operacional aprovada.

## Persistência / limites

API e coletor são processos separados supervisionados por `python run.py cloud`,
no mesmo serviço e volume. `STATE_DIR=/state` guarda SQLite/WAL, kill switch,
saldos virtuais, eventos, deduplicação e bloqueio Retry-After. Use uma única instância.
Sem volume, o estado será perdido; a aplicação não consegue verificar se um diretório
foi realmente montado. Faça backup com a API de backup do SQLite, não copie apenas
o arquivo principal enquanto há escrita/WAL. Não compartilhe esse SQLite entre hosts.
Separar API e worker em serviços Railway exigirá armazenamento compartilhado adequado
ou uma API de estado; isso fica para trabalho futuro, não foi implementado aqui.

Scanner: três pares, 500 barras em memória por par; retenção existente de eventos
e limite de threads=1. Monitore volume e memória: SQLite pode precisar de manutenção
offline para recuperar espaço físico. O supervisor encerra ambos se um processo morrer;
reconexões do feed continuam tratadas pelo coletor. `/health` confirma API, não feed;
verifique `/api/paper` para detectar estado stale/offline e clock circuit.
API somente leitura pela rede por padrão, kill remoto desabilitado. Para emergência
use console privado, `STATE_DIR=/state python -c "from lab.paper import Store; from lab.common import state_path; s=Store(state_path('paper.sqlite')); s.put('kill',True); s.close()"`.
Não habilite controle remoto numa implantação pública sem autenticação externa.

## Pesquisa pesada / dados

Não rode pesquisa, treinamento ou aquisição histórica no serviço contínuo.
Em máquina/job separado, execute `data` repetidamente até completar o manifesto,
depois `aggregate`, e `research --resume`. O config preserva 4 threads de aquisição,
2,5 GB novos por execução, 8 GB de teto local e 1.800 segundos por execução.
Arquivos já presentes são verificados antes de reutilização. 418/429 respeitam
Retry-After persistente. Arquivos sem disponibilidade permanecem explicitamente ausentes.
Checksum: https://github.com/binance/binance-public-data . Fontes:
https://data.binance.vision/ e https://data-api.binance.vision/ . Os parâmetros de
datas/pares e as fontes são preservados no config, no código e no manifesto de downloads.
O rebuild depende da disponibilidade da fonte; não é garantido reproduzir byte a byte
se a exchange revisar arquivos. Conserve os hashes e compare-os antes de interpretar
resultados. O teste de qualidade exige datasets reconstruídos; não confunda os testes
unitários com auditoria completa do dataset remoto.

`research/checkpoint.json` foi excluído: seus hashes eram do código anterior. `--resume`
validará hashes de execução e não deve reutilizar silenciosamente resultados antigos.
Resultados de novas pesquisas substituem arquivos; execute em outro checkout/diretório
ou preserve um snapshot antes. Não escolha modelos pelo melhor holdout já observado.

## Railway: configuração ainda necessária

1. Autorizar custos e criar serviço somente após decisão do usuário.
2. Conectar `djcorrea/AI-TRADER`, branch `main`, raiz `/`, Dockerfile existente.
3. Montar volume em `/state`, definir `STATE_DIR=/state`, `HOST=0.0.0.0`;
   PORT é fornecida pela plataforma. Uma instância, sem autoscaling horizontal.
4. Manter `ALLOW_REMOTE_CONTROL=0`, sem chaves da exchange; definir orçamento/limites.
5. Validar build Linux, acesso público REST/WebSocket Binance na região escolhida,
   HTTPS/WSS, escrita no volume e persistência após reinício. Disponibilidade geográfica
   da exchange não foi validada nesta migração.
6. Configurar backup, alertas sobre feed, uso de disco/CPU/RAM e política de retenção.

Documentação consultada: [Volumes Railway](https://docs.railway.com/volumes),
[referência](https://docs.railway.com/volumes/reference),
[Docker e PORT](https://blog.railway.com/p/deploy-scale-docker-containers-railway).
Nenhum serviço Railway foi criado ou pago e nenhuma conta de corretora conectada.
