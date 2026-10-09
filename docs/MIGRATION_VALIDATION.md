# Validação da migração

- Cópia local: 63 testes passaram; um aviso de depreciação Starlette/httpx.
- Integridade original: 284 arquivos selecionados mantiveram os hashes SHA256.
- Integridade de modelos: 36 arquivos joblib conferidos contra registry.json.
- Revisão automática dos arquivos selecionados: nenhum padrão de credencial ou path
  privado encontrado. Esse scan complementa a seleção de arquivos; não é garantia universal.
- Testes acrescentados: PORT/HOST, persistência/reabertura, health, bloqueio remoto,
  comandos contínuos sem treinamento e escolha WSS para HTTPS.
- Uma primeira execução dos 58 testes antigos passou as asserções, mas encerrou com
  erro de limpeza do temporário do Windows. A execução final usa diretório temporário
  isolado e retorna exit code 0.
- Docker não está disponível nesta máquina: build Linux e execução Railway ainda
  não foram validados. Workflow Ubuntu incluído para verificação após publicação.
- Nenhum novo backtest, promoção de estratégia ou deploy Railway realizado.
