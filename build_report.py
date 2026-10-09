"""Generate readable delivery from measured artifacts. Never invent missing metrics."""
import json,datetime,collections,zipfile
from pathlib import Path
from lab.common import ROOT,dump,sha,utc
from lab.paper import Store
def read(p,default):
    f=ROOT/p;return json.loads(f.read_text(encoding='utf-8')) if f.exists() else default
def pct(x):return 'indisponível' if x is None else f'{x*100:.3f}%'
def run():
    report=read('results/report.json',{});exp=read('results/experiments.json',[]);models=read('results/models.json',{});q=read('data/quality.json',{})
    manifest=read('data/download_manifest.json',{});counts=collections.Counter(r['status'] for r in manifest.get('records',[]))
    text=['# Resultados quantitativos efetivamente executados',f'Gerado: {utc()}',
        '\n**Nenhuma estratégia aprovada. Nenhum capital gasto ou conta de negociação conectada.**',
        f'\nDados: {sum(v["rows"] for v in q.values()):,} candles de 1 minuto; {len(q)} pares; arquivos mensais: {dict(counts)}.',
        f'Período coletado: {report.get("config",{}).get("start","indisponível")} a {report.get("config",{}).get("end_exclusive","indisponível")} exclusivo.',
        f'Backtests: {len(exp)}. Ajustes ML: {len(models.get("results",[]))}. Orçamento total: 120 experiências.',
        '\nOs períodos são cronológicos, mas históricos conhecidos. O final verdadeiramente prospectivo ainda não tem evidência de desempenho de estratégia ativa.',
        '\n## Especificações principais por período',
        '| Estratégia | Período | Retorno líquido | Negócios | PF | DD | Expectativa líquida por negócio | IC95% por blocos | IC por família | Decisão |',
        '|---|---|---:|---:|---:|---:|---:|---|---|---|']
    for e in exp:
        if e['variant']!=1 or e['scenario'] or e['strategy']=='random':continue
        m=e['metrics'];ci=' / '.join(pct(v) for v in m.get('ci95_block') or []) or 'indisponível'
        corr=' / '.join(pct(v) for v in m.get('ci_familywise') or []) or 'indisponível'
        pf='indisponível' if m['profit_factor'] is None else f'{m["profit_factor"]:.3f}'
        text.append(f'|{e["strategy"]}|{e["period"]}|{pct(m["net_return"])}|{m["trades"]}|{pf}|{pct(m["max_drawdown"])}|{pct(m["expectancy"])}|{ci}|{corr}|{e["status"]}|')
    text += ['\n## Comparação com controles','| Período | Caixa | Buy-and-hold líquido | DD buy-and-hold |','|---|---:|---:|---:|']
    for p,m in report.get('buy_hold',{}).items():text.append(f'|{p}|0%|{pct(m["net_return"])}|{pct(m["max_drawdown"])}|')
    text += ['\nBuy-and-hold: três candidatos mais líquidos elegíveis no início; pesos iguais; custos e filtros. Exposição diferente dos candidatos limitados por risco. Controles aleatórios usam probabilidade ex ante e as mesmas regras, sem pareamento perfeito de turnover.',
        '\n## Custos, disponibilidade e sensibilidades','|Experimento|Variante / cenário|Retorno|Negócios|PF|DD|Decisão|','|---|---|---:|---:|---:|---:|---|']
    for e in exp:
        if not e['scenario'] and e['variant']==1:continue
        m=e['metrics'];text.append(f'|{e["id"]}|{json.dumps(e["scenario"],ensure_ascii=False) or e["variant"]} / {e["variant"]}|{pct(m["net_return"])}|{m["trades"]}|{m["profit_factor"]}|{pct(m["max_drawdown"])}|{e["status"]}|')
    text += ['\n## Modelos: avaliação preditiva','|Modelo|Horizonte|Janela|Treino|Calibração|Teste|Brier|Brier constante|Candidatos|Média do rótulo líquido|','|---|---:|---|---:|---:|---:|---:|---:|---:|---:|']
    for m in models.get('results',[]):text.append(f'|{m["model"]}|{m["horizon_minutes"]}m|{m["begin"]} / {m["end"]}|{m["fit_rows"]}|{m["calibration_rows"]}|{m["test_rows"]}|{m["brier"]:.5f}|{m["null_brier"]:.5f}|{m["candidates"]}|{pct(m["candidate_label_net_mean"])}|')
    text += ['\n### Cobertura efetiva dos testes ML com limite de amostras','|Modelo|Horizonte / janela|Primeira disponibilidade avaliada UTC|Última disponibilidade avaliada UTC|','|---|---|---|---|']
    for m in models.get('results',[]):
        def iso(ms):return datetime.datetime.fromtimestamp(ms/1000,datetime.timezone.utc).isoformat()
        if 'actual_test_first_available_ms' in m:text.append(f'|{m["model"]}|{m["horizon_minutes"]}m / fold{m["fold"]}|{iso(m["actual_test_first_available_ms"])}|{iso(m["actual_test_last_available_ms"])}|')
    text += ['\n**Média de rótulos não é lucro de carteira.** Os rótulos se sobrepõem; o custo é embutido uma vez. As probabilidades são de três classes, calibradas em cauda cronológica de treino. Matrizes de confusão e curvas de calibração estão no JSON. O backtest ML aplica stops/targets e horizonte explícitos; isso constitui uma hipótese híbrida diferente do rótulo de retorno fixo e é avaliado separadamente.',
        '\n## Decisões e limites',str(dict(collections.Counter(e['status'] for e in exp))),
        '\nPF sem perdas fica indisponível; não exibimos infinito como evidência. Menos de 100 operações permanece inconclusivo mesmo com retorno negativo. Todos os experimentos, inclusive cancelamentos, perdas e períodos sem negócios, estão preservados.',
        '\nIntervalos: bootstrap circular por blocos de 7 dias calendários, 4.000 réplicas e correção Bonferroni para família de 120 experiências. A resolução Monte Carlo nas caudas corrigidas é limitada; isso reforça o bloqueio de promoção. A fração de réplicas não positivas é um diagnóstico bootstrap, não um teste exato sob hipótese nula.',
        '\nIC indisponível quando a amostra não cobre pelo menos 28 dias calendários e oito dias com negócios. Muitas operações concentradas em poucas sessões não contam como grande amostra independente.',
        '\n'+ '\n'.join('- '+x for x in report.get('limitations',[])),
        '\n## Próximo teste válido',
        'Congelar parâmetros, modelos e custos; manter observação prospectiva sem alterações; obter cotações públicas de execução, registrar todos os sinais elegíveis e recusados. Para validar estratégia ativa, primeiro resolver bloqueios de universo/filtros e demonstrar vantagem histórica robusta; só então simular a versão congelada em paper, sem dinheiro real. Exigir amostra suficiente em diferentes regimes, intervalo líquido positivo e estabilidade ao elevar custos. Se nenhuma hipótese passar, permanecer em caixa. Retreinar cria uma nova versão e uma nova avaliação, nunca apaga perdas anteriores.',
        '\n## Paper observado nesta entrega']
    s=Store(ROOT/'paper/paper.sqlite');service=s.get('service',{});conn=s.get('connectivity');events=s.db.execute("SELECT kind,count(*) FROM events GROUP BY kind").fetchall();s.close()
    text += [f'Estado no snapshot: `{json.dumps(service,ensure_ascii=False)}`',f'Conectividade: {conn}; eventos retidos: {dict(events)}.',
        'O corretor virtual está funcional e foi exercitado em testes sintéticos. Ao vivo, nenhuma hipótese foi aprovada, portanto não houve estratégia ativada nem negócios atribuídos a lucro real. Serviço local exige PC/rede/processo ligados.']
    (ROOT/'reports/RESULTADOS.md').write_text('\n'.join(text),encoding='utf-8')
    dump(ROOT/'reports/paper_observation_snapshot.json',{'at':utc(),'service':service,'connectivity':conn,'events_retained':dict(events)})
    sources={str(p.relative_to(ROOT)):sha(p) for p in ROOT.rglob('*') if p.is_file() and (p.suffix in ('.py','.html','.ini') or p.name in ['README.md','COBERTURA.md','AUDITORIA_V1.md','config.json','requirements-lock.txt']) and '__pycache__' not in p.parts}
    dump(ROOT/'reports/source_manifest.json',sources)
    # Portable source, reports, experiment evidence and model registry, excluding bulky public cache.
    dest=ROOT.parent/'quant-ai-v2-source.zip'
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
        baseline=ROOT.parent/'BASELINE_V1.zip'
        if not baseline.exists():baseline=ROOT/'BASELINE_V1.zip'
        if baseline.exists():z.write(baseline,'quant-ai-v2/BASELINE_V1.zip')
        for p in ROOT.rglob('*'):
            if not p.is_file() or any(k in p.parts for k in ('__pycache__','.pytest_cache','archives','parquet','derived')):continue
            if p.suffix in ('.sqlite','.duckdb') or p.name.endswith(('-wal','-shm','.log','.tmp')):continue
            if p.name=='BASELINE_V1.zip':continue
            z.write(p,'quant-ai-v2/'+str(p.relative_to(ROOT)))
    print(f'Report and portable source: {dest}',flush=True)
if __name__=='__main__':run()
