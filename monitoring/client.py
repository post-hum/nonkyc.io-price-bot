import requests
from requests.exceptions import RequestException, Timeout, ConnectionError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Optional, Dict
import logging
import urllib.parse

logger = logging.getLogger(__name__)

class NonKYCClient:
    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        logger.info("NonKYCClient initialized with base_url: %s", self.base_url)

    def _safe_float(self, val, default=0.0) -> float:
        if val is None:
            return default
        try:
            s = str(val).replace("+", "").replace("%", "").strip()
            return float(s) if s else default
        except (ValueError, TypeError):
            return default

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), retry=retry_if_exception_type((Timeout, ConnectionError)))
    def get_ticker(self, symbol: str) -> Optional[Dict]:
        sym = symbol.upper().replace("/", "_")
        encoded_sym = urllib.parse.quote(sym, safe='')
        url = f"{self.base_url}/ticker/{encoded_sym}"
        
        logger.debug("GET %s", url)
        
        try:
            r = self.session.get(url, timeout=self.timeout)
            logger.debug("Response status: %d for %s", r.status_code, sym)
            
            if r.status_code == 200:
                data = r.json()
                logger.debug("Parsed ticker data keys: %s", list(data.keys()) if isinstance(data, dict) else "not a dict")
                
                return {
                    "symbol": data.get("ticker_id", data.get("symbol", sym)),
                    "last": self._safe_float(data.get("last_price")),
                    "bid": self._safe_float(data.get("bid")),
                    "ask": self._safe_float(data.get("ask")),
                    "change_24h": self._safe_float(data.get("change_percent")),
                    "volume": self._safe_float(data.get("base_volume")),
                    "volume_quote": self._safe_float(data.get("target_volume")),
                    "high": self._safe_float(data.get("high")),
                    "low": self._safe_float(data.get("low")),
                    "timestamp": data.get("last_trade_at")
                }
            else:
                logger.warning("HTTP %d for %s: %s", r.status_code, sym, r.text[:200])
                return None
                
        except Exception as e:
            logger.error("Exception fetching %s: %s", sym, e, exc_info=True)
            return None

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), retry=retry_if_exception_type((Timeout, ConnectionError)))
    def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[Dict]:
        sym = symbol.upper().replace("/", "_")
        url = f"{self.base_url}/market/orderbook"
        logger.debug("GET %s?symbol=%s&limit=%d", url, sym, limit)
        
        try:
            r = self.session.get(url, params={"symbol": sym, "limit": limit}, timeout=self.timeout)
            logger.debug("Orderbook response: %d", r.status_code)
            
            if r.status_code != 200:
                return None
                
            data = r.json()
            bids = [(self._safe_float(b.get("numberprice") or b.get("price")), self._safe_float(b.get("quantity"))) 
                   for b in data.get("bids", [])[:limit]]
            asks = [(self._safe_float(a.get("numberprice") or a.get("price")), self._safe_float(a.get("quantity"))) 
                   for a in data.get("asks", [])[:limit]]
            return {"bids": bids, "asks": asks, "symbol": sym}
        except Exception as e:
            logger.error("Orderbook error for %s: %s", sym, e)
            return None

    def normalize_symbol(self, symbol: str) -> str:
        return symbol.replace("/", "_").upper()
