#!/usr/bin/env python3
"""
EN590 COMMODITIES GROUP — Price Updater
Fetches real commodity prices and updates index.html
Runs automatically via GitHub Actions every 6 hours
"""

import re
import json
import requests
from datetime import datetime, timezone

# ══════════════════════════════════════════════
#  FETCH PRICES FROM YAHOO FINANCE (FREE)
# ══════════════════════════════════════════════

SYMBOLS = {
    "BZ=F":  ("BRENT CRUDE",        "bbl"),
    "CL=F":  ("WTI CRUDE",          "bbl"),
    "NG=F":  ("NAT GAS TTF",        "MMBtu"),
}

def fetch_yahoo_price(symbol):
    """Fetch price from Yahoo Finance API - completely free."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        result = data["chart"]["result"][0]
        price = result["meta"]["regularMarketPrice"]
        prev  = result["meta"]["chartPreviousClose"]
        change_pct = ((price - prev) / prev * 100) if prev else 0
        trend = "up" if change_pct >= 0 else "down"
        arrow = "▲" if trend == "up" else "▼"
        sign  = "+" if change_pct >= 0 else ""
        return {
            "price":  f"${price:.2f}",
            "change": f"{sign}{change_pct:.2f}%",
            "trend":  trend,
            "arrow":  arrow,
        }
    except Exception as e:
        print(f"  ⚠️  Yahoo error for {symbol}: {e}")
        return None


def build_prices():
    """
    Build full price dict.
    Yahoo Finance for oil/gas, fixed estimates for others
    (Diesel, Sulphur, Urea, NPK are OTC — no free real-time API)
    """
    print("📡 Fetching prices from Yahoo Finance...")
    prices = {}

    # Real-time from Yahoo
    for symbol, (name, unit) in SYMBOLS.items():
        p = fetch_yahoo_price(symbol)
        if p:
            prices[name] = {
                "price":  f"{p['price']}/{unit}",
                "change": p["change"],
                "trend":  p["trend"],
                "arrow":  p["arrow"],
            }
            print(f"  ✅ {name}: {p['price']}/{unit} {p['arrow']} {p['change']}")

    # OTC products — indicative (update manually or add paid API)
    # These are realistic market estimates
    otc = [
        ("EN590 Diesel",       "$746/MT",      "+0.18%", "up"),
        ("Jet Fuel A-1",       "$820/MT",      "+0.55%", "up"),
        ("Mazut M100",         "$310/MT",      "−0.15%", "down"),
        ("Bitumen 60/70",      "$420/MT",      "+0.08%", "up"),
        ("Sulphur Gran 99.5%", "$112/MT",      "−0.44%", "down"),
        ("Urea 46% Gran",      "$298/MT",      "+1.12%", "up"),
        ("NPK 16-16-16",       "$340/MT",      "−0.28%", "down"),
    ]
    for name, price, change, trend in otc:
        arrow = "▲" if trend == "up" else "▼"
        prices[name] = {
            "price":  price,
            "change": change,
            "trend":  trend,
            "arrow":  arrow,
        }

    return prices


# ══════════════════════════════════════════════
#  UPDATE index.html
# ══════════════════════════════════════════════

def update_html(prices):
    """Updates price data in index.html"""

    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    now_utc = datetime.now(timezone.utc).strftime("%B %d, %Y · %H:%M UTC")

    # ── 1. Update ticker bar prices ──
    # Pattern: <span class="val">$XX.XX</span> next to each ticker item
    ticker_map = {
        "BRENT CRUDE":   prices.get("BRENT CRUDE",  {}).get("price", "$82.14"),
        "WTI CRUDE":     prices.get("WTI CRUDE",    {}).get("price", "$78.90"),
        "EN590 10PPM":   prices.get("EN590 Diesel", {}).get("price", "$746/MT"),
        "SULPHUR GRAN":  prices.get("Sulphur Gran 99.5%", {}).get("price", "$112/MT"),
        "UREA 46% GRAN": prices.get("Urea 46% Gran",{}).get("price", "$298/MT"),
        "NPK 16-16-16":  prices.get("NPK 16-16-16", {}).get("price", "$340/MT"),
        "JET FUEL A1":   prices.get("Jet Fuel A-1", {}).get("price", "$820/MT"),
        "MAZUT M100":    prices.get("Mazut M100",   {}).get("price", "$310/MT"),
        "NAT GAS TTF":   prices.get("NAT GAS TTF",  {}).get("price", "$10.42/MMBtu"),
        "BITUMEN 60/70": prices.get("Bitumen 60/70",{}).get("price", "$420/MT"),
    }

    # Update each ticker item value
    for name, price in ticker_map.items():
        # Match: <span class="val">OLD_PRICE</span> after the name
        pattern = rf'(<span class="name">{re.escape(name)}</span><span class="val">)[^<]+(</span>)'
        replacement = rf'\g<1>{price}\g<2>'
        html = re.sub(pattern, replacement, html)

    # ── 2. Update hero price card ──
    hero_map = {
        "EN590 Diesel":      ("EN590 Diesel",       "price-val", prices.get("EN590 Diesel",      {}).get("price", "$746")),
        "Brent Crude":       ("BRENT CRUDE",         "price-val", prices.get("BRENT CRUDE",       {}).get("price", "$82.14")),
        "Sulphur Gran 99.5%":("Sulphur Granulated",  "price-val", prices.get("Sulphur Gran 99.5%",{}).get("price", "$112")),
        "Urea 46% Gran":     ("Urea 46%",            "price-val", prices.get("Urea 46% Gran",     {}).get("price", "$298")),
        "NPK 16-16-16":      ("NPK Fertilizer",      "price-val", prices.get("NPK 16-16-16",      {}).get("price", "$340")),
    }

    # ── 3. Update market stats cards ──
    # EN590 Rotterdam
    en590_price = prices.get("EN590 Diesel", {}).get("price", "$746/MT").replace("/MT","")
    html = re.sub(
        r'(EN590 Rotterdam FOB.*?<div class="s-val">)[^<]+(</div>)',
        rf'\g<1>{en590_price}\g<2>',
        html, flags=re.DOTALL
    )

    # Urea Black Sea
    urea_price = prices.get("Urea 46% Gran", {}).get("price", "$298/MT").replace("/MT","")
    html = re.sub(
        r'(Urea 46% Black Sea FOB.*?<div class="s-val">)[^<]+(</div>)',
        rf'\g<1>{urea_price}\g<2>',
        html, flags=re.DOTALL
    )

    # Sulphur ME
    sulphur_price = prices.get("Sulphur Gran 99.5%", {}).get("price", "$112/MT").replace("/MT","")
    html = re.sub(
        r'(Sulphur Gran\. ME FOB.*?<div class="s-val">)[^<]+(</div>)',
        rf'\g<1>{sulphur_price}\g<2>',
        html, flags=re.DOTALL
    )

    # Nat Gas TTF
    gas_price = prices.get("NAT GAS TTF", {}).get("price", "$10.42/MMBtu").replace("/MMBtu","")
    html = re.sub(
        r'(Nat\. Gas TTF Spot.*?<div class="s-val">)[^<]+(</div>)',
        rf'\g<1>{gas_price}\g<2>',
        html, flags=re.DOTALL
    )

    # ── 4. Update "Updated daily" timestamp ──
    html = re.sub(
        r'Updated daily',
        f'Updated {now_utc}',
        html
    )

    # ── 5. Inject prices as JS variable for chart ──
    brent_js = prices.get("BRENT CRUDE", {}).get("price", "$82.14").replace("$","")
    wti_js   = prices.get("WTI CRUDE",   {}).get("price", "$78.90").replace("$","")

    js_injection = f"""
    // AUTO-UPDATED BY GITHUB ACTIONS — {now_utc}
    var LIVE_BRENT = {brent_js};
    var LIVE_WTI   = {wti_js};
    """

    html = re.sub(
        r'// AUTO-UPDATED BY GITHUB ACTIONS.*?var LIVE_WTI.*?;',
        js_injection.strip(),
        html, flags=re.DOTALL
    )

    # If first run — inject before closing </script>
    if "LIVE_BRENT" not in html:
        html = html.replace(
            "// ═══════════════════════",
            js_injection + "\n// ═══════════════════════",
            1
        )

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n✅ index.html updated successfully!")
    print(f"⏰ Timestamp: {now_utc}")
    return True


# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════

if __name__ == "__main__":
    print("═" * 50)
    print("  EN590 Price Updater — GitHub Actions")
    print("═" * 50)

    prices = build_prices()
    update_html(prices)

    print("\n📊 Final prices:")
    for name, data in prices.items():
        arrow = data.get("arrow", "")
        print(f"  {arrow} {name}: {data['price']} {data['change']}")

    print("\n✅ Done!")
