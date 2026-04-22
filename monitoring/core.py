import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any, Tuple
from datetime import datetime
from .client import NonKYCClient

logger = logging.getLogger(__name__)

@dataclass
class MarketData:
    symbol: str
    timestamp: datetime = field(default_factory=datetime.now)
    bid: float = 0.0
    ask: float = 0.0
    last: float = 0.0
    change_24h: float = 0.0
    volume_24h: float = 0.0
    bids: List[Tuple[float, float]] = field(default_factory=list)
    asks: List[Tuple[float, float]] = field(default_factory=list)
    events: List[Dict] = field(default_factory=list)
    raw_data: Dict = field(default_factory=dict)

    @property
    def mid_price(self) -> float:
        return (self.bid + self.ask) / 2 if self.bid and self.ask else self.last or 0.0

    @property
    def spread_pct(self) -> float:
        return ((self.ask - self.bid) / self.mid_price) * 100 if self.mid_price > 0 else 0.0

class MarketMonitor:
    def __init__(self, client: NonKYCClient, symbol: str, interval: int = 60):
        self.client = client
        self.symbol = symbol.upper().replace("_", "/")
        self.interval = interval
        self._subscribers: List[Callable[[MarketData], Any]] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._prev_data: Optional[MarketData] = None

    def subscribe(self, callback: Callable[[MarketData], Any]):
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[MarketData], Any]):
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _emit(self, data: MarketData):
        for callback in self._subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(data))
                else:
                    callback(data)
            except Exception as e:
                logger.error("Subscriber error: %s", e)

    def _fetch_data(self) -> Optional[MarketData]:
        """Synchronous data fetch - uses blocking requests."""
        ticker = self.client.get_ticker(self.symbol)
        if not ticker:
            return None
        try:
            data = MarketData(
                symbol=self.symbol,
                bid=float(ticker.get("bid", 0)),
                ask=float(ticker.get("ask", 0)),
                last=float(ticker.get("last", ticker.get("price", 0))),
                change_24h=float(ticker.get("change_24h", ticker.get("percentChange", 0))),
                volume_24h=float(ticker.get("volume", ticker.get("volume_24h", 0))),
                raw_data=ticker
            )
            ob = self.client.get_orderbook(self.symbol, limit=10)
            if ob:
                data.bids = [(float(b[0]), float(b[1])) for b in ob.get("bids", [])[:10]]
                data.asks = [(float(a[0]), float(a[1])) for a in ob.get("asks", [])[:10]]
            return data
        except (ValueError, KeyError, TypeError) as e:
            logger.error("Data parse error for %s: %s", self.symbol, e)
            return None

    def _check_conditions(self, current: MarketData, prev: Optional[MarketData]) -> List[Dict]:
        events = []
        if not prev:
            return events
        if prev.last > 0:
            pct_change = ((current.last - prev.last) / prev.last) * 100
            if abs(pct_change) >= 1.0:
                events.append({"type": "price_change_percent", "value": pct_change, "direction": "up" if pct_change > 0 else "down", "message": f"Price changed by {abs(pct_change):.2f}%"})
        if prev.volume_24h > 0 and current.volume_24h > 0:
            vol_change = ((current.volume_24h - prev.volume_24h) / prev.volume_24h) * 100
            if abs(vol_change) >= 50:
                events.append({"type": "volume_spike", "value": vol_change, "direction": "up" if vol_change > 0 else "down", "message": f"Volume changed by {abs(vol_change):.1f}%"})
        if current.bids:
            price, qty = current.bids[0]
            if qty > 10000:
                events.append({"type": "orderbook_depth", "value": qty, "direction": "bid", "message": f"Large bid wall: {qty:.0f} @ ${price:.6f}"})
        if current.asks:
            price, qty = current.asks[0]
            if qty > 10000:
                events.append({"type": "orderbook_depth", "value": qty, "direction": "ask", "message": f"Large ask wall: {qty:.0f} @ ${price:.6f}"})
        return events

    async def _monitor_loop(self):
        while self._running:
            try:
                current = await asyncio.to_thread(self._fetch_data)
                if not current:
                    await asyncio.sleep(self.interval)
                    continue
                events = self._check_conditions(current, self._prev_data)
                current.events = events
                self._emit(current)
                self._prev_data = current
            except Exception as e:
                logger.error("Monitor loop error: %s", e)
            await asyncio.sleep(self.interval)

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._monitor_loop())

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    @property
    def is_running(self) -> bool:
        return self._running
