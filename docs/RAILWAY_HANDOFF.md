# Railway — implantação preparada, ainda não autorizada

## Configuração a aplicar depois da autenticação e autorização de gasto

Use o serviço existente quando houver um. Não crie projeto, serviço, volume ou
assinatura antes de conferir o plano, consumo existente e autorização do usuário.

| Campo | Valor |
|---|---|
| Source / branch | `djcorrea/AI-TRADER`, `codex/quant-ai-v3-cloud-handoff` |
| Build / Builder | Dockerfile existente, `Dockerfile` |
| Deploy / Start Command | `python run.py cloud` |
| Deploy / Healthcheck Path | `/health` |
| Deploy / Replicas | 1, uma região, sem autoscaling |
| Deploy / Replica Limits | Proposta: 1 vCPU e 1 GB RAM; revisar RSS após warmup |
| Deploy / Serverless | Desativado para observação contínua |
| Volume / Mount Path | `/state` |
| Volume / Size | Proposta: 5 GB; revisar uso e retenção antes de reduzir |
| Variables / HOST | `0.0.0.0` |
| Variables / PORT | Deixar a plataforma fornecer; não fixar porta local |
| Variables / STATE_DIR | `/state` |
| Variables / ALLOW_REMOTE_CONTROL | `0` |
| Variables / OMP_NUM_THREADS, OPENBLAS_NUM_THREADS, MKL_NUM_THREADS | `1` |

Não configurar chaves de negociação, `CONTROL_TOKEN` ou controles remotos.
O dashboard público não contém botão administrativo. `/api/kill` está desativado
por padrão, inclusive para loopback/cliente encaminhado por proxy. Se habilitado
explicitamente em outro ambiente, exige Bearer autenticado; Origin não autentica.

O processo permanente inicia somente API e coletor. Reconstrução histórica,
discovery, comparação e treinamento devem ocorrer no workspace de pesquisa.
Não copiar datasets, bancos locais, `.env` ou credenciais para a imagem.

## Custos propostos em USD

Fonte oficial consultada em 09/10/2026: `railwayapp/docs`, commit
`b2c0106946259493aa0d51c0b3a47e861a457f6a`,
[`content/docs/pricing/plans.md`](https://github.com/railwayapp/docs/blob/b2c0106946259493aa0d51c0b3a47e861a457f6a/content/docs/pricing/plans.md).

RAM: US$10/GB/mês; CPU: US$20/vCPU/mês; volume: US$0,15/GB/mês;
egress: US$0,05/GB. Hobby: mínimo US$5/mês, incluindo US$5 de consumo.
Pro: mínimo US$20/mês, incluindo US$20. Não somar novamente o crédito ao consumo.

Para uma instância com média estimada de 0,5–0,8 GB RAM, 0,05–0,15 vCPU,
5 GB de volume e 1–10 GB de egress/mês:

`consumo = RAM × 10 + CPU × 20 + volume × 0,15 + egress × 0,05`

Estimativa: **US$6,80–12,25/mês** em Hobby. São hipóteses, não medição mensal.
O teste inicial de API + coletor observou aproximadamente 0,46 GB de RSS somado;
CPU e tráfego de visitantes ainda não têm uma janela representativa no Railway.
Uma instância limitada a 1 GB e 1 vCPU pode consumir US$30,75/mês mais egress
se permanecer no máximo; o dashboard público pode aumentar o tráfego.

O plano Free oferece US$1 de crédito recorrente e recursos menores; não foi
considerado suficiente para observação contínua. Trial não garante continuidade.
Custos totais dependem de outros serviços e créditos do workspace. Não foi
contratada assinatura nem criado recurso. Impostos e câmbio não estão incluídos.

O volume de 5 GB acomoda a hipótese de retenção de eventos por 90 dias e o cache
limitado do feed. Fills persistidos não são apagados automaticamente. Monitorar
ocupação; não guardar histórico bruto de pesquisa no volume do serviço.

Após conferir outros serviços, pode-se propor alerta de consumo US$8 e limite
US$15 em Workspace / Usage / Set Usage Limits. Esse limite interrompe **todos**
os serviços do workspace ao ser atingido e também requer concordância; não foi
alterado. Não habilitar recursos de Railway Agent.

## Validação depois do deploy

1. Confirmar revisão/commit implantado, volume `/state`, uma réplica e variáveis.
2. GET `/health`: API disponível, `real_trading=false`; inspecionar também `feed`.
   A plataforma usa a disponibilidade da API para evitar ciclos de restart em
   uma interrupção externa da Binance; feed indisponível aparece explicitamente.
3. GET `/api/paper`: `connectivity=connected`, mensagens recentes, candles e
   cotações frescos. `feed_health` registra idade, quantidade de quotes frescas
   e cobertura do universo monitorado. Confirmar relógio, sem posições aprovadas.
4. GET `/`: sem controles administrativos. POST `/api/kill`: HTTP 403.
5. Registrar estado, saldo, último candle processado e um marcador de teste via
   shell administrativo autenticado do Railway; reiniciar a instância e confirmar
   o mesmo SQLite/estado. Remover apenas o marcador de teste. Não simular fill.
6. Revalidar feed na região escolhida e reconexão. Build e teste local não
   comprovam disponibilidade regional nem persistência no Railway.

## Rede do Cloud Environment

Em configurações do ambiente: manter acesso **Restricted** e os presets atuais.
No campo de domínios adicionais (`network.allowed_domains`), manter:

| Domínio exato | Uso |
|---|---|
| `data.binance.vision` | ZIPs históricos e arquivos `.CHECKSUM` |
| `data-api.binance.vision` | REST público: time, exchangeInfo e klines |
| `data-stream.binance.vision` | WebSocket público de bookTicker e kline |
| `s3-ap-northeast-1.amazonaws.com` | Catálogo histórico usado pelo código |
| `backboard.railway.com` | Autenticação e API de gerenciamento da CLI Railway |

Instalação da CLI usa `github.com` e `release-assets.githubusercontent.com`,
já presentes no preset. Login humano usa `railway.com/activate` no navegador do
usuário; não requer ampliar acesso da aplicação. Nenhum wildcard foi solicitado.
O domínio público do serviço só poderá ser identificado depois da implantação;
para validar pela nuvem, adicionar somente esse hostname exato se houver bloqueio.

O rascunho deve ser **revisado, salvo e publicado** no Cloud Environment.
Salvar o rascunho via ferramenta não aplica a política nem publica o ambiente.
O metadado atual ainda não lista os hosts personalizados, mas os probes reais
da Binance e o fluxo OAuth Railway passaram nesta sessão; validar novamente após
publicação. Se necessário, autenticar pela CLI `railway login --browserless` e
aprovar no navegador. Nunca colocar senhas/tokens em chat, Git ou Dockerfile.
