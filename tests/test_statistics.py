from lab.stats import block_ci
def test_clustered_trades_do_not_get_zero_width_confidence():
    trades=[{'exit_t':(i//100)*86400000,'net_return':-.003} for i in range(300)]
    assert block_ci(trades)==(None,None,None)
def test_many_calendar_days_but_too_few_trade_days():
    trades=[{'exit_t':i*100*86400000,'net_return':.001} for i in range(7)]
    assert block_ci(trades)==(None,None,None)
