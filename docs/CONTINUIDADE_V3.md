# Continuidade V3 na nuvem

Leia `reports/AUDITORIA_V2.md` antes de interpretar os artefatos antigos. V3 está em desenvolvimento; nenhuma estratégia aprovada.

## Fluxo validado

Python 3.13, versões do `requirements-lock.txt` preservadas. Neste ambiente:

```sh
source .venv/bin/activate
python -m pytest -q
python run.py audit
STATE_DIR=/workspace/onboarding/runtime python run.py cloud --host 127.0.0.1 --port 4174
```

API/dashboard e SQLite funcionam. Os probes atuais confirmaram REST, arquivos/checksums, catálogo e WebSocket públicos; o feed real monitora 27 pares. `/health` informa disponibilidade da API e saúde do feed separadamente; confirme idade das mensagens e cobertura de cotações também em `/api/paper`. O scanner seleciona os candidatos do config que a exchange confirma como Spot USDT atualmente listados; observa até 100, com 500 barras por ativo. O modelo predeclarado `v3_logistic_30m_fold2` é publicado em um artefato de aproximadamente 3 KB, com registry novo, hash/config conferidos e status `SHADOW_ONLY`. A inferência fica limitada ao universo de treino BTC/ETH/SOL; o shadow original permanece preservado. Nenhum shadow pode submeter ordens; todos os pares permanecem `NO_TRADE`.

`/api/audit` apresenta a reconciliação parcial. `/api/data-rebuild` apresenta o snapshot da auditoria de recuperação, e `/api/research-v3` o piloto isolado. `/api/opportunities` consulta o mapa no volume ou, quando ausente, um resumo publicado explicitamente limitado. Sem nenhum deles, informa indisponibilidade. Nenhum dado ausente é preenchido artificialmente com zero.

Os artefatos históricos ficam preservados como resultados da V2. Os dados da aba Laboratório são metadados reportados pela V2; sua existência não indica que os candles correspondentes já estejam disponíveis na nuvem.

## Retomar aquisição e diagnóstico

Valide `/api/v3/time` e o checksum de um arquivo antes de iniciar downloads. O novo comando `rebuild` preserva os metadados migrados da V2, verifica caches, limita o streaming dos downloads, expansão dos ZIPs e disco e mantém logs separados em `STATE_DIR/rebuild`. Um arquivo com integridade suspeita interrompe o lote e permanece preservado. Compare fontes originais com `git show d987229e25f8cf69391c33bc5ba8b77dbe386d58:data/download_manifest.json` ao avaliar reprodução da V2. Não rode dois processos escrevendo o mesmo mês/ativo ou os mesmos ponteiros de STATE_DIR.

```sh
python run.py rebuild --max-archives 24 --max-seconds 300
# Repetir lotes; aumente até 720 arquivos / 1800 segundos dentro do orçamento.
python audit_rebuild.py
python run.py rebuild --symbols BTCUSDT ETHUSDT SOLUSDT --end-date 2026-10-01 --max-archives 27 --max-seconds 300
# A data exclusiva inclui os arquivos mensais até setembro/2026.
python run.py discovery --max-rows 100000 --max-seconds 300
```

O end-date não altera o config congelado da V2. Arquivos do mês corrente podem ainda não existir; o scanner coleta apenas observações atuais, não recompõe silenciosamente todo esse mês. Aquisição diária/REST incremental persistida para fechar esse intervalo continua pendente.

O mapa usa somente Parquet e ZIP com hashes conferidos, exige janelas futuras contínuas e registra fontes/períodos. Grava runs separados em `STATE_DIR/opportunities` ou `paper/opportunities`. É retrospectivo: MFE/MAE e primeira passagem usam futuro somente para diagnóstico. Os grupos contêm ativo, regime, hora/dia UTC, horizonte, volatilidade, volume e estatísticas; a API faz consultas parametrizadas com no máximo 200 linhas.

Períodos 2024–2025 já foram observados. Os novos dados também não são classificados como teste virgem por padrão. Não rode o antigo `research` para substituir a evidência histórica. O novo `research-v3 --max-seconds 900` exige os 24 meses auditados de BTC/ETH/SOL, grava fontes/configuração antes dos experimentos e preserva runs em `STATE_DIR/v3-research`. São seis regras de três famílias, três variantes somente em descoberta, parâmetros fixos em validação/teste, cenários de custos e controles. O piloto inicial concluiu 39 backtests (22 rejeitados, 17 inconclusivos), três folds de regressão logística de 30 minutos e sete candidatos preditivos no último fold. Nenhuma estratégia foi aprovada; o último fold é predeclarado para shadow, sem seleção pelo lucro ou permissão paper. Os testes de ML têm cap de 10 mil linhas por fold, cobrindo apenas parte do intervalo nominal; datas efetivas estão nos artefatos. A comparação completa do universo e hipóteses novas continuam pendentes.

## Railway

CLI 5.64.1 em `/workspace/.cloud-tools/bin/railway`. O rascunho contém instalação e domínios; precisa ser revisado/salvo e publicado para aplicação. Login e deployment não foram concluídos.

O serviço usa `python run.py cloud`, uma instância e volume persistente em `/state`. `HOST=0.0.0.0`, `STATE_DIR=/state`, `ALLOW_REMOTE_CONTROL=0`; PORT vem do Railway. Nenhuma chave de corretora. O Dockerfile original foi preservado. O build local usa uma cópia temporária com a CA pública montada como segredo de BuildKit para manter a verificação TLS no proxy; a CA não é gravada na imagem.

Os processos não sobrevivem necessariamente à publicação. Execute os comandos de startup salvos e confirme respostas funcionais e persistência do SQLite. Build local não comprova deploy nem acesso ao feed na região Railway. Consulte `docs/RAILWAY_HANDOFF.md` para os campos exatos, custos e validações. Recursos com cobrança exigem autorização prévia; nenhuma contratação ocorreu.

## Comparação ampliada e cobertura final

Após qualificar os 681 pares de arquivos disponíveis da V2, a mesma pesquisa predefinida foi executada sobre os 30 candidatos manuais, preservando o piloto anterior. Foram mais 39 backtests: 23 rejeitados e 16 inconclusivos; as seis regras principais perderam dinheiro no teste retrospectivo. Os três folds logísticos repetiram byte a byte os modelos do piloto, pois o universo de ML permaneceu BTC/ETH/SOL. A nova contabilidade, taxas, drawdowns, Brier, hashes e purga temporal passaram em conferência independente. Evidência em `reports/v3_research_full.json` e `/api/research-v3/full`. Nenhum candidato paper.

A recuperação de janeiro–setembro/2026 também foi concluída: 243 arquivos disponíveis, com 27 meses indisponíveis dos símbolos antigos MATIC/RNDR/EOS. São 924 ZIPs/Parquets verificados no total; o snapshot registra quantidade de candles, hashes, datas e ausência. Os 39 arquivos indisponíveis na cobertura original permanecem documentados; não se afirma que migrações/listings estejam completamente resolvidos. Outubro/2026 não foi reconstruído por arquivos diários: o scanner mantém as observações recebidas desde esta sessão.

```sh
python run.py rebuild --start-date 2026-01-01 --end-date 2026-10-01 --max-archives 270 --max-seconds 900
python audit_rebuild.py
python run.py research-v3 --full-universe --max-seconds 900
```

`rebuild` aceita início por mês para evitar reprocessar todo o cache em extensões. O comparativo amplo continua sendo retrospectivo, sobre universo manual incompleto e execução hipotética. Manter carteira em caixa até vantagem estatística e elegibilidade prospectiva comprovadas.

O coletor recupera candles públicos já fechados se o aquecimento/reconexão perder um minuto. A consulta REST é limitada pelo close time do evento processado e exclui o próprio candle antes de adicioná-lo uma única vez. Isso evita usar futuro; lacunas reais na fonte continuam visíveis e reiniciam features.
