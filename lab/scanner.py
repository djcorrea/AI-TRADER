"""Lightweight public-market screening; no order or model-approval methods."""
import math


def monitor_symbols(records, candidates, maximum=100):
    available = {r['symbol'] for r in records
                 if r.get('status') == 'TRADING'
                 and r.get('quoteAsset') == 'USDT'
                 and r.get('isSpotTradingAllowed', True)}
    return list(dict.fromkeys(s for s in candidates if s in available))[:maximum]


def finite(value):
    try:
        return float(value) if math.isfinite(float(value)) else None
    except (TypeError, ValueError):
        return None


def observation(symbol, candle, feature, previous_volume, quote, now):
    fresh = bool(quote and 0 <= now-quote['received'] <= 3)
    spread = (quote['ask']/quote['bid']-1
              if fresh and quote['bid'] > 0 and quote['ask'] >= quote['bid'] else None)
    relative = candle['v']/previous_volume if previous_volume and previous_volume > 0 else None
    return {'symbol': symbol, 'candle_close_ms': candle['ct'], 'price': candle['c'],
            'regime': str(feature['regime']), 'rsi': finite(feature['rsi']),
            'atrn': finite(feature['atrn']), 'quote_volume_candle': candle['qv'],
            'relative_volume': finite(relative), 'spread': finite(spread),
            'data_status': 'CLOSED_CANDLE', 'eligibility': 'OBSERVATION_ONLY',
            'historical_opportunity': None, 'decision': 'NO_TRADE',
            'reason': 'No paper candidate approved; current listing is not proof of historical eligibility'}
