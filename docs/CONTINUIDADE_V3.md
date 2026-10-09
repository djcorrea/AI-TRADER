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

API/dashboard e SQLite funcionam. O coletor está impedido de obter dados públicos pela rede atual. `/health` verifica a API; `/api/paper` precisa ser inspecionado separadamente. O scanner seleciona os candidatos do config que a exchange confirma como Spot USDT atualmente listados; observa até 100, com 500 barras por ativo, e mantém inferência do modelo antigo limitada ao universo de treino. Sem estratégia aprovada, todos permanecem `NO_TRADE`.

`/api/audit` apresenta a reconciliação parcial. `/api/opportunities` mostra indisponibilidade até que exista um mapa construído com dados verificados. Nenhum dado ausente é preenchido artificialmente com zero.

Os artefatos históricos ficam preservados como resultados da V2. Os dados da aba Laboratório são metadados reportados pela V2; sua existência não indica que os candles correspondentes já estejam disponíveis na nuvem.

## Retomar aquisição e diagnóstico

Após os domínios da Binance estarem aplicados, valide `/api/v3/time` e o checksum de um arquivo antes de iniciar downloads. O script original de aquisição altera metadados de coleta; o snapshot V2 foi preservado. Compare fontes originais com `git show d987229e25f8cf69391c33bc5ba8b77dbe386d58:data/download_manifest.json` ao avaliar reprodução da V2.

```sh
python run.py data
# Repetir conforme os limites por execução, até obter a cobertura original.
python audit_data.py
python run.py data --end-date 2026-10-01
# A data exclusiva inclui os arquivos mensais até setembro/2026.
python run.py discovery --max-rows 100000 --max-seconds 300
```

O end-date não altera o config congelado da V2. Arquivos do mês corrente podem ainda não existir; o scanner coleta apenas observações atuais, não recompõe silenciosamente todo esse mês. Aquisição diária/REST incremental persistida para fechar esse intervalo continua pendente.

O mapa usa somente Parquet e ZIP com hashes conferidos, exige janelas futuras contínuas e registra fontes/períodos. Grava runs separados em `STATE_DIR/opportunities` ou `paper/opportunities`. É retrospectivo: MFE/MAE e primeira passagem usam futuro somente para diagnóstico. Os grupos contêm ativo, regime, hora/dia UTC, horizonte, volatilidade, volume e estatísticas; a API faz consultas parametrizadas com no máximo 200 linhas.

Períodos 2024–2025 já foram observados. Os novos dados também não são classificados como teste virgem por padrão. Antes de treinamento, registre exposição, congele hipóteses e divida descoberta/validação/teste de forma temporal; não rode o antigo `research` para substituir a evidência histórica sem preparar um run isolado e manter o baseline.

## Railway

CLI 5.64.1 em `/workspace/.cloud-tools/bin/railway`. O rascunho contém instalação e domínios; precisa ser revisado/salvo e publicado para aplicação. Login e deployment não foram concluídos.

O serviço usa `python run.py cloud`, uma instância e volume persistente em `/state`. `HOST=0.0.0.0`, `STATE_DIR=/state`, `ALLOW_REMOTE_CONTROL=0`; PORT vem do Railway. Nenhuma chave de corretora. O Dockerfile original foi preservado. O build local usa uma cópia temporária com a CA pública montada como segredo de BuildKit para manter a verificação TLS no proxy; a CA não é gravada na imagem.

Os processos não sobrevivem necessariamente à publicação. Execute os comandos de startup salvos e confirme respostas funcionais e persistência do SQLite. Build local não comprova deploy nem acesso ao feed na região Railway. A missão não autoriza contratar serviços pagos.
