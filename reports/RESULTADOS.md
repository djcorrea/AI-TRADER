# Resultados quantitativos efetivamente executados
Gerado: 2026-10-09T01:18:03.640153+00:00

**Nenhuma estratégia aprovada. Nenhum capital gasto ou conta de negociação conectada.**

Dados: 29,814,300 candles de 1 minuto; 30 pares; arquivos mensais: {'OK': 681, 'NOT_AVAILABLE': 39}.
Período coletado: 2024-01-01 a 2026-01-01 exclusivo.
Backtests: 80. Ajustes ML: 36. Orçamento total: 120 experiências.

Os períodos são cronológicos, mas históricos conhecidos. O final verdadeiramente prospectivo ainda não tem evidência de desempenho de estratégia ativa.

## Especificações principais por período
| Estratégia | Período | Retorno líquido | Negócios | PF | DD | Expectativa líquida por negócio | IC95% por blocos | IC por família | Decisão |
|---|---|---:|---:|---:|---:|---:|---|---|---|
|trend|discovery|-8.063%|125|0.675|-10.006%|-0.260%|indisponível|indisponível|REJEITADA|
|trend|validation|-8.240%|153|0.631|-10.151%|-0.229%|indisponível|indisponível|REJEITADA|
|trend|retrospective_holdout|-10.074%|98|0.274|-10.254%|-0.435%|indisponível|indisponível|INCONCLUSIVO|
|pullback|discovery|-0.117%|1|0.000|-0.117%|-0.471%|indisponível|indisponível|INCONCLUSIVO|
|pullback|validation|-0.450%|5|0.559|-1.235%|-0.444%|indisponível|indisponível|INCONCLUSIVO|
|pullback|retrospective_holdout|-0.396%|1|0.000|-0.396%|-2.625%|indisponível|indisponível|INCONCLUSIVO|
|breakout|discovery|-9.310%|81|0.457|-10.103%|-0.732%|indisponível|indisponível|INCONCLUSIVO|
|breakout|validation|-9.697%|88|0.398|-10.303%|-0.475%|indisponível|indisponível|INCONCLUSIVO|
|breakout|retrospective_holdout|-9.991%|81|0.166|-10.193%|-0.527%|indisponível|indisponível|INCONCLUSIVO|
|mean_regime|discovery|-9.357%|129|0.545|-10.057%|-0.318%|-0.590% / -0.023%|-0.757% / 0.158%|REJEITADA|
|mean_regime|validation|-10.398%|99|0.335|-10.434%|-0.442%|-0.665% / -0.184%|-0.761% / -0.028%|INCONCLUSIVO|
|mean_regime|retrospective_holdout|-10.101%|79|0.189|-10.101%|-0.557%|-0.663% / -0.397%|-0.748% / -0.267%|INCONCLUSIVO|
|cross_momentum|discovery|-8.587%|83|0.518|-10.233%|-0.552%|indisponível|indisponível|INCONCLUSIVO|
|cross_momentum|validation|-7.432%|128|0.664|-10.059%|-0.227%|indisponível|indisponível|REJEITADA|
|cross_momentum|retrospective_holdout|-9.582%|175|0.611|-10.274%|-0.249%|indisponível|indisponível|REJEITADA|
|relative_btc|discovery|-7.147%|101|0.659|-10.208%|-0.370%|indisponível|indisponível|REJEITADA|
|relative_btc|validation|-6.550%|195|0.810|-10.066%|-0.241%|indisponível|indisponível|REJEITADA|
|relative_btc|retrospective_holdout|-8.574%|163|0.667|-10.015%|-0.245%|indisponível|indisponível|REJEITADA|
|compression|discovery|-10.169%|89|0.438|-10.169%|-0.473%|indisponível|indisponível|INCONCLUSIVO|
|compression|validation|-10.337%|107|0.366|-10.407%|-0.406%|indisponível|indisponível|REJEITADA|
|compression|retrospective_holdout|-10.108%|96|0.243|-10.108%|-0.434%|indisponível|indisponível|INCONCLUSIVO|
|range|discovery|-9.360%|163|0.557|-10.157%|-0.229%|indisponível|indisponível|REJEITADA|
|range|validation|-10.121%|138|0.405|-10.121%|-0.320%|indisponível|indisponível|REJEITADA|
|range|retrospective_holdout|-10.234%|119|0.163|-10.234%|-0.370%|indisponível|indisponível|REJEITADA|
|volume_anomaly|discovery|-9.624%|66|0.385|-10.292%|-0.533%|indisponível|indisponível|INCONCLUSIVO|
|volume_anomaly|validation|-8.925%|117|0.512|-10.108%|-0.281%|indisponível|indisponível|REJEITADA|
|volume_anomaly|retrospective_holdout|-9.988%|76|0.189|-10.056%|-0.571%|indisponível|indisponível|INCONCLUSIVO|
|hybrid|discovery|-9.664%|80|0.451|-10.085%|-0.520%|indisponível|indisponível|INCONCLUSIVO|
|hybrid|validation|-7.636%|138|0.625|-10.107%|-0.234%|indisponível|indisponível|REJEITADA|
|hybrid|retrospective_holdout|-9.987%|98|0.309|-10.189%|-0.440%|indisponível|indisponível|INCONCLUSIVO|

## Comparação com controles
| Período | Caixa | Buy-and-hold líquido | DD buy-and-hold |
|---|---:|---:|---:|
|discovery|0%|33.909%|-39.353%|
|validation|0%|-1.660%|-46.147%|
|retrospective_holdout|0%|-6.239%|-43.056%|

Buy-and-hold: três candidatos mais líquidos elegíveis no início; pesos iguais; custos e filtros. Exposição diferente dos candidatos limitados por risco. Controles aleatórios usam probabilidade ex ante e as mesmas regras, sem pareamento perfeito de turnover.

## Custos, disponibilidade e sensibilidades
|Experimento|Variante / cenário|Retorno|Negócios|PF|DD|Decisão|
|---|---|---:|---:|---:|---:|---|
|001_trend_discovery|{} / 0.9|-8.843%|118|0.635862661907057|-10.213%|REJEITADA|
|003_trend_discovery|{} / 1.1|-9.560%|117|0.570164600706871|-10.019%|REJEITADA|
|006_trend_retrospective_holdout|{"fee": 0.0015, "spread_half": 0.001, "slippage": 0.001, "fill_fraction": 0.5} / 1.0|-10.030%|120|0.12278295470204455|-10.084%|REJEITADA|
|007_trend_retrospective_holdout|{"outage": true, "latency_bars": 2} / 1.0|-10.061%|89|0.21440789296813187|-10.085%|INCONCLUSIVO|
|008_pullback_discovery|{} / 0.9|0.000%|0|None|0.000%|INCONCLUSIVO|
|010_pullback_discovery|{} / 1.1|-3.875%|21|0.15682189478802913|-4.273%|INCONCLUSIVO|
|013_pullback_retrospective_holdout|{"fee": 0.0015, "spread_half": 0.001, "slippage": 0.001, "fill_fraction": 0.5} / 1.0|-0.195%|1|0.0|-0.195%|INCONCLUSIVO|
|014_pullback_retrospective_holdout|{"outage": true, "latency_bars": 2} / 1.0|0.308%|1|None|-0.140%|INCONCLUSIVO|
|015_breakout_discovery|{} / 0.9|-9.615%|159|0.6772911893324819|-10.424%|REJEITADA|
|017_breakout_discovery|{} / 1.1|-9.418%|136|0.6290695547048165|-10.170%|REJEITADA|
|020_breakout_retrospective_holdout|{"fee": 0.0015, "spread_half": 0.001, "slippage": 0.001, "fill_fraction": 0.5} / 1.0|-10.019%|102|0.05574720799070048|-10.102%|REJEITADA|
|021_breakout_retrospective_holdout|{"outage": true, "latency_bars": 2} / 1.0|-10.255%|90|0.17209089425614682|-10.318%|INCONCLUSIVO|
|022_mean_regime_discovery|{} / 0.9|-9.475%|139|0.5548160242236462|-10.028%|REJEITADA|
|024_mean_regime_discovery|{} / 1.1|-9.434%|141|0.586541752002905|-10.102%|REJEITADA|
|027_mean_regime_retrospective_holdout|{"fee": 0.0015, "spread_half": 0.001, "slippage": 0.001, "fill_fraction": 0.5} / 1.0|-10.333%|113|0.1032871172165646|-10.333%|REJEITADA|
|028_mean_regime_retrospective_holdout|{"outage": true, "latency_bars": 2} / 1.0|-10.007%|90|0.1877190245944202|-10.007%|INCONCLUSIVO|
|029_cross_momentum_discovery|{} / 0.9|-9.415%|163|0.6851936637656428|-10.158%|REJEITADA|
|031_cross_momentum_discovery|{} / 1.1|-8.419%|80|0.4654858939839816|-10.147%|INCONCLUSIVO|
|034_cross_momentum_retrospective_holdout|{"fee": 0.0015, "spread_half": 0.001, "slippage": 0.001, "fill_fraction": 0.5} / 1.0|-10.093%|177|0.3600259764870924|-10.137%|REJEITADA|
|035_cross_momentum_retrospective_holdout|{"outage": true, "latency_bars": 2} / 1.0|-9.835%|123|0.4288020835458092|-10.185%|REJEITADA|
|036_relative_btc_discovery|{} / 0.9|-8.035%|96|0.6020088429909451|-10.082%|INCONCLUSIVO|
|038_relative_btc_discovery|{} / 1.1|-7.768%|177|0.7657993679982301|-10.066%|REJEITADA|
|041_relative_btc_retrospective_holdout|{"fee": 0.0015, "spread_half": 0.001, "slippage": 0.001, "fill_fraction": 0.5} / 1.0|-10.036%|197|0.4529692974601609|-10.142%|REJEITADA|
|042_relative_btc_retrospective_holdout|{"outage": true, "latency_bars": 2} / 1.0|-9.393%|197|0.6634137147405718|-10.149%|REJEITADA|
|043_compression_discovery|{} / 0.9|-10.098%|92|0.4348941128504722|-10.098%|INCONCLUSIVO|
|045_compression_discovery|{} / 1.1|-10.080%|108|0.49817981152701246|-10.103%|REJEITADA|
|048_compression_retrospective_holdout|{"fee": 0.0015, "spread_half": 0.001, "slippage": 0.001, "fill_fraction": 0.5} / 1.0|-10.058%|119|0.10899173451960684|-10.058%|REJEITADA|
|049_compression_retrospective_holdout|{"outage": true, "latency_bars": 2} / 1.0|-10.187%|94|0.2651994217051436|-10.187%|INCONCLUSIVO|
|050_range_discovery|{} / 0.9|-9.845%|166|0.5585456124096594|-10.333%|REJEITADA|
|052_range_discovery|{} / 1.1|-9.568%|151|0.5096890603175673|-10.097%|REJEITADA|
|055_range_retrospective_holdout|{"fee": 0.0015, "spread_half": 0.001, "slippage": 0.001, "fill_fraction": 0.5} / 1.0|-10.199%|134|0.04234835729296109|-10.199%|REJEITADA|
|056_range_retrospective_holdout|{"outage": true, "latency_bars": 2} / 1.0|-10.141%|104|0.10766518430660002|-10.141%|REJEITADA|
|057_volume_anomaly_discovery|{} / 0.9|-9.590%|57|0.30027502157253166|-10.165%|INCONCLUSIVO|
|059_volume_anomaly_discovery|{} / 1.1|-9.459%|69|0.4025792189841621|-10.080%|INCONCLUSIVO|
|062_volume_anomaly_retrospective_holdout|{"fee": 0.0015, "spread_half": 0.001, "slippage": 0.001, "fill_fraction": 0.5} / 1.0|-10.082%|106|0.08826020814418638|-10.099%|REJEITADA|
|063_volume_anomaly_retrospective_holdout|{"outage": true, "latency_bars": 2} / 1.0|-10.123%|78|0.2050940481696014|-10.158%|INCONCLUSIVO|
|064_hybrid_discovery|{} / 0.9|-9.796%|108|0.5394389195194205|-10.216%|REJEITADA|
|066_hybrid_discovery|{} / 1.1|-9.805%|101|0.5219301791541465|-10.225%|REJEITADA|
|069_hybrid_retrospective_holdout|{"fee": 0.0015, "spread_half": 0.001, "slippage": 0.001, "fill_fraction": 0.5} / 1.0|-9.989%|153|0.29737041964372846|-10.072%|REJEITADA|
|070_hybrid_retrospective_holdout|{"outage": true, "latency_bars": 2} / 1.0|-10.097%|152|0.5338826243285097|-10.160%|REJEITADA|
|071_random_validation|{"random_seed": 20261009} / 1.0|-10.070%|98|0.31670243382297997|-10.070%|INCONCLUSIVO|
|072_random_retrospective_holdout|{"random_seed": 20261009} / 1.0|-10.082%|136|0.3376558419981829|-10.082%|REJEITADA|
|073_random_validation|{"random_seed": 20261010} / 1.0|-10.084%|95|0.2658226484927631|-10.109%|INCONCLUSIVO|
|074_random_retrospective_holdout|{"random_seed": 20261010} / 1.0|-10.055%|144|0.36057992725439464|-10.055%|REJEITADA|
|075_random_validation|{"random_seed": 20261011} / 1.0|-9.787%|118|0.39756165116302306|-10.084%|REJEITADA|
|076_random_retrospective_holdout|{"random_seed": 20261011} / 1.0|-10.041%|114|0.33185136422636086|-10.119%|REJEITADA|
|113_ml_retrospective_holdout|{"ml_horizon_minutes": 5, "interval_minutes": 1} / 1.0|0.000%|0|None|0.000%|INCONCLUSIVO|
|114_ml_retrospective_holdout|{"ml_horizon_minutes": 15, "interval_minutes": 1} / 1.0|0.000%|0|None|0.000%|INCONCLUSIVO|
|115_ml_retrospective_holdout|{"ml_horizon_minutes": 30, "interval_minutes": 1} / 1.0|0.000%|0|None|0.000%|INCONCLUSIVO|
|116_ml_retrospective_holdout|{"ml_horizon_minutes": 60, "interval_minutes": 1} / 1.0|0.000%|0|None|0.000%|INCONCLUSIVO|

## Modelos: avaliação preditiva
|Modelo|Horizonte|Janela|Treino|Calibração|Teste|Brier|Brier constante|Candidatos|Média do rótulo líquido|
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
|logistic|5m|2025-01-01 / 2025-04-01|80000|20000|20000|0.02022|0.02147|0|indisponível|
|random_forest|5m|2025-01-01 / 2025-04-01|80000|20000|20000|0.01984|0.02147|0|indisponível|
|lightgbm|5m|2025-01-01 / 2025-04-01|80000|20000|20000|0.01979|0.02147|0|indisponível|
|logistic|5m|2025-04-01 / 2025-07-01|80000|20000|20000|0.00974|0.01010|0|indisponível|
|random_forest|5m|2025-04-01 / 2025-07-01|80000|20000|20000|0.00974|0.01010|0|indisponível|
|lightgbm|5m|2025-04-01 / 2025-07-01|80000|20000|20000|0.00974|0.01010|0|indisponível|
|logistic|5m|2025-07-01 / 2026-01-01|80000|20000|20000|0.00693|0.00713|0|indisponível|
|random_forest|5m|2025-07-01 / 2026-01-01|80000|20000|20000|0.00692|0.00713|0|indisponível|
|lightgbm|5m|2025-07-01 / 2026-01-01|80000|20000|20000|0.00689|0.00713|0|indisponível|
|logistic|15m|2025-01-01 / 2025-04-01|80000|20000|20000|0.05187|0.05597|0|indisponível|
|random_forest|15m|2025-01-01 / 2025-04-01|80000|20000|20000|0.05096|0.05597|0|indisponível|
|lightgbm|15m|2025-01-01 / 2025-04-01|80000|20000|20000|0.05079|0.05597|0|indisponível|
|logistic|15m|2025-04-01 / 2025-07-01|80000|20000|20000|0.03569|0.03748|0|indisponível|
|random_forest|15m|2025-04-01 / 2025-07-01|80000|20000|20000|0.03555|0.03748|0|indisponível|
|lightgbm|15m|2025-04-01 / 2025-07-01|80000|20000|20000|0.03551|0.03748|0|indisponível|
|logistic|15m|2025-07-01 / 2026-01-01|80000|20000|20000|0.02760|0.02893|0|indisponível|
|random_forest|15m|2025-07-01 / 2026-01-01|80000|20000|20000|0.02753|0.02893|0|indisponível|
|lightgbm|15m|2025-07-01 / 2026-01-01|80000|20000|20000|0.02745|0.02893|0|indisponível|
|logistic|30m|2025-01-01 / 2025-04-01|80000|20000|20000|0.08532|0.09072|1|-0.056%|
|random_forest|30m|2025-01-01 / 2025-04-01|80000|20000|20000|0.08310|0.09072|0|indisponível|
|lightgbm|30m|2025-01-01 / 2025-04-01|80000|20000|20000|0.08287|0.09072|0|indisponível|
|logistic|30m|2025-04-01 / 2025-07-01|80000|20000|20000|0.06628|0.06946|0|indisponível|
|random_forest|30m|2025-04-01 / 2025-07-01|80000|20000|20000|0.06545|0.06946|0|indisponível|
|lightgbm|30m|2025-04-01 / 2025-07-01|80000|20000|20000|0.06536|0.06946|0|indisponível|
|logistic|30m|2025-07-01 / 2026-01-01|80000|20000|20000|0.05531|0.05845|0|indisponível|
|random_forest|30m|2025-07-01 / 2026-01-01|80000|20000|20000|0.05515|0.05845|0|indisponível|
|lightgbm|30m|2025-07-01 / 2026-01-01|80000|20000|20000|0.05503|0.05845|0|indisponível|
|logistic|60m|2025-01-01 / 2025-04-01|80000|20000|20000|0.12401|0.13131|3|-1.187%|
|random_forest|60m|2025-01-01 / 2025-04-01|80000|20000|20000|0.12159|0.13131|0|indisponível|
|lightgbm|60m|2025-01-01 / 2025-04-01|80000|20000|20000|0.12164|0.13131|20|-0.514%|
|logistic|60m|2025-04-01 / 2025-07-01|80000|20000|20000|0.10956|0.11458|1|-7.803%|
|random_forest|60m|2025-04-01 / 2025-07-01|80000|20000|20000|0.10804|0.11458|0|indisponível|
|lightgbm|60m|2025-04-01 / 2025-07-01|80000|20000|20000|0.10799|0.11458|0|indisponível|
|logistic|60m|2025-07-01 / 2026-01-01|80000|20000|20000|0.09635|0.10162|0|indisponível|
|random_forest|60m|2025-07-01 / 2026-01-01|80000|20000|20000|0.09588|0.10162|0|indisponível|
|lightgbm|60m|2025-07-01 / 2026-01-01|80000|20000|20000|0.09577|0.10162|0|indisponível|

### Cobertura efetiva dos testes ML com limite de amostras
|Modelo|Horizonte / janela|Primeira disponibilidade avaliada UTC|Última disponibilidade avaliada UTC|
|---|---|---|---|
|logistic|5m / fold0|2025-01-01T00:00:59.999000+00:00|2025-03-11T10:30:59.999000+00:00|
|random_forest|5m / fold0|2025-01-01T00:00:59.999000+00:00|2025-03-11T10:30:59.999000+00:00|
|lightgbm|5m / fold0|2025-01-01T00:00:59.999000+00:00|2025-03-11T10:30:59.999000+00:00|
|logistic|5m / fold1|2025-04-01T00:00:59.999000+00:00|2025-06-09T10:30:59.999000+00:00|
|random_forest|5m / fold1|2025-04-01T00:00:59.999000+00:00|2025-06-09T10:30:59.999000+00:00|
|lightgbm|5m / fold1|2025-04-01T00:00:59.999000+00:00|2025-06-09T10:30:59.999000+00:00|
|logistic|5m / fold2|2025-07-01T00:00:59.999000+00:00|2025-09-08T10:30:59.999000+00:00|
|random_forest|5m / fold2|2025-07-01T00:00:59.999000+00:00|2025-09-08T10:30:59.999000+00:00|
|lightgbm|5m / fold2|2025-07-01T00:00:59.999000+00:00|2025-09-08T10:30:59.999000+00:00|
|logistic|15m / fold0|2025-01-01T00:00:59.999000+00:00|2025-03-11T10:30:59.999000+00:00|
|random_forest|15m / fold0|2025-01-01T00:00:59.999000+00:00|2025-03-11T10:30:59.999000+00:00|
|lightgbm|15m / fold0|2025-01-01T00:00:59.999000+00:00|2025-03-11T10:30:59.999000+00:00|
|logistic|15m / fold1|2025-04-01T00:00:59.999000+00:00|2025-06-09T10:30:59.999000+00:00|
|random_forest|15m / fold1|2025-04-01T00:00:59.999000+00:00|2025-06-09T10:30:59.999000+00:00|
|lightgbm|15m / fold1|2025-04-01T00:00:59.999000+00:00|2025-06-09T10:30:59.999000+00:00|
|logistic|15m / fold2|2025-07-01T00:00:59.999000+00:00|2025-09-08T10:30:59.999000+00:00|
|random_forest|15m / fold2|2025-07-01T00:00:59.999000+00:00|2025-09-08T10:30:59.999000+00:00|
|lightgbm|15m / fold2|2025-07-01T00:00:59.999000+00:00|2025-09-08T10:30:59.999000+00:00|
|logistic|30m / fold0|2025-01-01T00:00:59.999000+00:00|2025-03-11T10:30:59.999000+00:00|
|random_forest|30m / fold0|2025-01-01T00:00:59.999000+00:00|2025-03-11T10:30:59.999000+00:00|
|lightgbm|30m / fold0|2025-01-01T00:00:59.999000+00:00|2025-03-11T10:30:59.999000+00:00|
|logistic|30m / fold1|2025-04-01T00:00:59.999000+00:00|2025-06-09T10:30:59.999000+00:00|
|random_forest|30m / fold1|2025-04-01T00:00:59.999000+00:00|2025-06-09T10:30:59.999000+00:00|
|lightgbm|30m / fold1|2025-04-01T00:00:59.999000+00:00|2025-06-09T10:30:59.999000+00:00|
|logistic|30m / fold2|2025-07-01T00:00:59.999000+00:00|2025-09-08T10:30:59.999000+00:00|
|random_forest|30m / fold2|2025-07-01T00:00:59.999000+00:00|2025-09-08T10:30:59.999000+00:00|
|lightgbm|30m / fold2|2025-07-01T00:00:59.999000+00:00|2025-09-08T10:30:59.999000+00:00|
|logistic|60m / fold0|2025-01-01T00:00:59.999000+00:00|2025-03-11T10:30:59.999000+00:00|
|random_forest|60m / fold0|2025-01-01T00:00:59.999000+00:00|2025-03-11T10:30:59.999000+00:00|
|lightgbm|60m / fold0|2025-01-01T00:00:59.999000+00:00|2025-03-11T10:30:59.999000+00:00|
|logistic|60m / fold1|2025-04-01T00:00:59.999000+00:00|2025-06-09T10:30:59.999000+00:00|
|random_forest|60m / fold1|2025-04-01T00:00:59.999000+00:00|2025-06-09T10:30:59.999000+00:00|
|lightgbm|60m / fold1|2025-04-01T00:00:59.999000+00:00|2025-06-09T10:30:59.999000+00:00|
|logistic|60m / fold2|2025-07-01T00:00:59.999000+00:00|2025-09-08T10:30:59.999000+00:00|
|random_forest|60m / fold2|2025-07-01T00:00:59.999000+00:00|2025-09-08T10:30:59.999000+00:00|
|lightgbm|60m / fold2|2025-07-01T00:00:59.999000+00:00|2025-09-08T10:30:59.999000+00:00|

**Média de rótulos não é lucro de carteira.** Os rótulos se sobrepõem; o custo é embutido uma vez. As probabilidades são de três classes, calibradas em cauda cronológica de treino. Matrizes de confusão e curvas de calibração estão no JSON. O backtest ML aplica stops/targets e horizonte explícitos; isso constitui uma hipótese híbrida diferente do rótulo de retorno fixo e é avaliado separadamente.

## Decisões e limites
{'REJEITADA': 44, 'INCONCLUSIVO': 36}

PF sem perdas fica indisponível; não exibimos infinito como evidência. Menos de 100 operações permanece inconclusivo mesmo com retorno negativo. Todos os experimentos, inclusive cancelamentos, perdas e períodos sem negócios, estão preservados.

Intervalos: bootstrap circular por blocos de 7 dias calendários, 4.000 réplicas e correção Bonferroni para família de 120 experiências. A resolução Monte Carlo nas caudas corrigidas é limitada; isso reforça o bloqueio de promoção. A fração de réplicas não positivas é um diagnóstico bootstrap, não um teste exato sob hipótese nula.

IC indisponível quando a amostra não cobre pelo menos 28 dias calendários e oito dias com negócios. Muitas operações concentradas em poucas sessões não contam como grande amostra independente.

- Manual candidate universe: historical volume ranking reduces but does not eliminate selection bias
- Current filters are proxies, not historically point-in-time filters
- Historical spread/slippage/partial fills are scenario assumptions, not observed execution
- Both intrabar barriers touched: stop wins and ambiguity logged; market gaps may exceed risk limit
- 2024-2025 has already been seen in V1; chronological holdout is retrospective and not pristine
- No FX conversion cost, taxes, hosting or downtime of the PC priced into returns
- ML sample cap and stride; conditional net payoff assumptions may change under a new regime
- No full combinatorial purged CV or HMM; synchronized expanding folds with purge and embargo used
- Block confidence and Bonferroni guard do not establish stationarity or guarantee future returns

## Próximo teste válido
Congelar parâmetros, modelos e custos; manter observação prospectiva sem alterações; obter cotações públicas de execução, registrar todos os sinais elegíveis e recusados. Para validar estratégia ativa, primeiro resolver bloqueios de universo/filtros e demonstrar vantagem histórica robusta; só então simular a versão congelada em paper, sem dinheiro real. Exigir amostra suficiente em diferentes regimes, intervalo líquido positivo e estabilidade ao elevar custos. Se nenhuma hipótese passar, permanecer em caixa. Retreinar cria uma nova versão e uma nova avaliação, nunca apaga perdas anteriores.

## Paper observado nesta entrega
Estado no snapshot: `{"status": "running", "updated": "2026-10-09T01:18:02.104990+00:00", "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"], "messages": 27732, "real_orders": false, "paper_pnl_brl": 0.0, "active_positions": 0, "mode": "prospective observation; promotion blocked", "elapsed_seconds": 220.0051521000005}`
Conectividade: connected; eventos retidos: {'closed_candle': 48, 'connected': 4, 'raw_feed': 99955, 'scanner': 96, 'shadow_prediction': 60}.
O corretor virtual está funcional e foi exercitado em testes sintéticos. Ao vivo, nenhuma hipótese foi aprovada, portanto não houve estratégia ativada nem negócios atribuídos a lucro real. Serviço local exige PC/rede/processo ligados.