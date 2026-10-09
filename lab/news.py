"""Disabled interface. Mock events are for tests only and never research evidence."""
from dataclasses import dataclass
@dataclass(frozen=True)
class NewsEvent:
    published_ms:int
    available_ms:int
    headline:str
    source:str
    mock:bool=False
def causal_news(events,decision_ms,research=True):
    return [e for e in events if e.published_ms<=e.available_ms<=decision_ms and not (research and e.mock)]
