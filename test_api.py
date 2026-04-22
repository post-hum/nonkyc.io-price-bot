import requests, json
BASE = "https://api.nonkyc.io/api/v2"
SYMBOL = "XLA/USDT"
for path in ["/market/ticker", "/tickers", "/markets", "/price", f"/markets/{SYMBOL}/ticker"]:
    url = BASE + path
    print(f"\n🔍 {url}")
    try:
        r = requests.get(url, params={"symbol": SYMBOL, "market": SYMBOL}, timeout=5)
        print(f"Status: {r.status_code}")
        print(r.text[:300])
    except Exception as e:
        print(f"Error: {e}")
