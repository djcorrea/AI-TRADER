# QUANT AI V3 — handoff cloud, 09/10/2026

## 1. Publicação e preservação

Branch: [`codex/quant-ai-v3-cloud-handoff`](https://github.com/djcorrea/AI-TRADER/tree/codex/quant-ai-v3-cloud-handoff).
Primeiro checkpoint publicado: `41f29d05908a62fa1955c3dc6c683a5fdf3f9118`.
Correções de segurança e recuperação: `37b5b6ee5dd422706ddc87ce30c3cc99202ab683`.
O commit final do handoff segue nessa mesma branch; não houve force push nem
alteração de `main`. Foram conferidos 258 arquivos protegidos da V2/V1, incluindo
modelos, resultados, metadados de dados, relatórios históricos, config, locks,
Dockerfile e Railway: todos permanecem byte a byte iguais ao baseline `d987229`.

Nenhuma credencial, `.env`, SQLite, DuckDB, cache bruto ou dataset de candles foi
incluído nas alterações publicadas. O modelo novo para shadow tem 3.126 bytes e
hash conferido; os demais artefatos novos publicados são código e resumos de
pesquisa/auditoria. O cache de aproximadamente 3,6 GB permanece ignorado pelo Git.

## 2. Cloud Environment

Python 3.13.15, dependências bloqueadas e Railway CLI 5.64.1 instalados. Scripts,
instruções e checkout foram salvos no rascunho. A configuração ainda precisa de
**Review → Save → Publish** no painel do Cloud Environment. A skill
`cloud-environment-onboarding:setup` exige essa etapa do usuário: salvar o rascunho
pela ferramenta não aplica ou publica o ambiente. Restauração em uma nova tarefa
não foi independentemente validada; não presumir que caches/processos sobrevivem.

Manter acesso Restricted e presets atuais. Em `network.allowed_domains`, manter
`data.binance.vision`, `data-api.binance.vision`, `data-stream.binance.vision`,
`s3-ap-northeast-1.amazonaws.com` e `backboard.railway.com`. Usos e campos detalhados
em `docs/RAILWAY_HANDOFF.md`. Os probes e feed reais passaram nesta sessão, embora
o metadado observado ainda não listasse os hosts personalizados. Proxy e TLS foram
preservados; nenhuma restrição foi contornada.

## 3. Dados reconstruídos e auditados

- 681 ZIPs/Parquets disponíveis do baseline: hashes do ZIP e Parquet iguais aos originais.
- Mais 243 arquivos disponíveis de janeiro–setembro/2026.
- **924 pares, 40.428.540 candles de um minuto, zero erros e zero lacunas detectadas.**
- 39 arquivos indisponíveis na cobertura original e 27 meses indisponíveis de
  MATIC/RNDR/EOS em 2026 documentados, sem preenchimento artificial.
- Outubro/2026 não foi reconstruído por arquivos diários; o feed registra
  observações novas desde o início desta sessão. Listings, migrações, filtros e
  livro histórico permanecem incompletos.

Aquisição sequencial: orçamento de 2,5 GB de download e 8 GB de dados; o lote
original terminou em menos de 1.800 segundos. Extensão recente terminou dentro de
900 segundos. ZIPs limitados em streaming e expansão; checksums do publicador,
hashes, finitude, duplicatas, timestamps, OHLC, volumes e lacunas verificados.
Manifestos V2 não foram substituídos. Runs/auditorias em STATE_DIR; resumo durável
em `reports/v3_rebuild_summary.json`.

## 4. Verificações

92 testes passaram. Há um aviso de depreciação Starlette/httpx, sem falha.
Reconciliação independente V2: 80 backtests e 36 modelos preservados.
Piloto e comparação V3: saldo, taxas, drawdown, Brier, candidatos, hashes e purga
temporal conferidos. JavaScript passou na verificação de sintaxe.
Build Docker e execução nativa passaram; estado SQLite e kill anterior persistiram
após reinício com volume. API, feed público e ausência de controles administrativos
foram conferidos. Isso ainda não valida rede/volume na região Railway.

## 5. Railway e custos

Nenhum projeto vinculado ou deployment realizado. CLI ainda não autenticada;
login oficial browserless requer confirmação humana. Não transmitir senha/token
em chat. Nenhuma assinatura, serviço ou volume com cobrança foi criado.

Proposta preparada: Dockerfile existente, `python run.py cloud`, HOST=0.0.0.0,
PORT da plataforma, STATE_DIR=/state, volume de 5 GB em /state, uma instância,
limites de 1 vCPU/1 GB, sem autoscaling e ALLOW_REMOTE_CONTROL=0. Sem credenciais
ou operações reais; sem treinamento no serviço permanente.

Hobby: **US$6,80–12,25/mês estimados**, conforme premissas e tabela oficial em
`docs/RAILWAY_HANDOFF.md`; consumo máximo da réplica pode ser US$30,75 mais
egress. O plano/consumo real da conta não foi conferido. Aprovação e limite de
gasto são necessários antes de criar recursos. Limite de workspace compartilhado
pode desligar outros serviços e não deve ser alterado sem concordância.

## 6. Funcionalidades operacionais

- Scanner público de 27 pares atualmente listados; dados de candles fechados e
  cotações, detecção de frescor e reconexão. Todos `NO_TRADE`.
- `/health` distingue API disponível de feed saudável; `/api/paper` expõe estado,
  idade das mensagens e cobertura de cotações. Pares com cotação antiga não são
  tratados como preços executáveis.
- Shadow V3 predeclarado em BTC/ETH/SOL, hash/config conferidos e registro
  `SHADOW_ONLY`. Zero ordens e zero posições; estimativas não são lucro.
- Mapa com dados reais dos 30 candidatos, horizontes 5/15/30/60/240 minutos,
  regimes, hora/dia, volume, volatilidade, MFE/MAE e cenários hipotéticos de custos.
  Mapa completo no volume de desenvolvimento; resumo publicado contém 300 grupos
  de exemplo e é explicitamente limitado.
- 39 backtests no piloto (22 rejeitados/17 inconclusivos), mais 39 no universo
  manual (23 rejeitados/16 inconclusivos). Nenhuma vantagem aprovada. Três folds
  logísticos repetiram modelos idênticos nos dois runs; sete candidatos preditivos
  no último fold continuam sem elegibilidade paper. Os testes de ML têm cap de
  dez mil linhas/fold e não cobrem todo o período nominal.
- Dashboard público sem botão administrativo. POST `/api/kill` é 403 por padrão;
  habilitação explícita em outro ambiente exige Bearer autenticado.

Evidências: `reports/v3_research_pilot.json`, `reports/v3_research_full.json`,
`reports/v3_opportunities.json`, `reports/v3_audit.json` e `/workspace/onboarding/`.
Artefatos completos de cada run permanecem separados; capital virtual R$500,
capital real R$0 e carteira em caixa.

## 7. Bloqueios e limites restantes

Publicação do Cloud Environment, autenticação Railway, autorização de gasto e
verificação do plano/projeto/volume. Após deploy, validar feed regional e SQLite
após restart. Sem conta verificada, não afirmar que a integração está pronta.

Limites científicos: universo manual, custos e filtros históricos assumidos,
sequência intrabar/fila maker não observadas, histórico 2024–2025 já exposto,
retornos de labels sobrepostos e ausência de amostra prospectiva suficiente.
O mapa expõe também os dados recentes; eles não são declarados teste virgem.
Reprodução completa de todas as pesquisas/treinos V2 e qualificação de hipóteses
novas permanecem pendentes. Não baixar gates para criar operações.

## 8. Próxima ação

Revisar/salvar/publicar o rascunho cloud e concluir o login Railway no navegador.
Responder à autorização de custo proposta. Depois conferir o projeto e teto,
implantar a revisão publicada e validar `/health`, `/api/paper`, feed e persistência
na região. Continuar observação prospectiva com versões congeladas; paper só
quando houver candidato elegível. A V3 não está concluída nem demonstrou lucro.
