import yfinance as yf
import pandas as pd
import requests
from datetime import datetime

# ===== TELEGRAM CONFIG =====
TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ===== DATA =====
data = yf.download("^NSEI", period="1d", interval="5m")

if data.empty or len(data) < 20:
    print("No data")
    exit()

# ===== VWAP =====
data['VWAP'] = (data['Close'] * data['Volume']).cumsum() / data['Volume'].cumsum()

# ===== RSI =====
delta = data['Close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)

rs = gain.rolling(14).mean() / loss.rolling(14).mean()
data['RSI'] = 100 - (100 / (1 + rs))

# ===== LAST VALUES =====
latest = data.iloc[-1]
prev = data.iloc[-2]

price = float(latest['Close'])
vwap = float(latest['VWAP'])
rsi = float(latest['RSI'])

high = float(prev['High'])
low = float(prev['Low'])

signal = "❌ No Trade"

entry = "-"
sl = "-"
target = "-"

# ===== STRATEGY =====

# 📈 CALL
if price > vwap and rsi > 55 and price > high:
    entry = round(price, 2)
    sl = round(price * 0.90, 2)
    target = round(price * 1.15, 2)

    signal = f"""📈 BUY CALL

Entry: {entry}
SL: {sl}
Target: {target}
RSI: {round(rsi,1)}
VWAP: {round(vwap,1)}"""

# 📉 PUT
elif price < vwap and rsi < 45 and price < low:
    entry = round(price, 2)
    sl = round(price * 0.90, 2)
    target = round(price * 1.15, 2)

    signal = f"""📉 BUY PUT

Entry: {entry}
SL: {sl}
Target: {target}
RSI: {round(rsi,1)}
VWAP: {round(vwap,1)}"""

# ===== MESSAGE =====
msg = f"""⚡ NIFTY OPTION SIGNAL
🕒 {datetime.now()}

Price: {price}

{signal}
"""

print(msg)

send_telegram(msg)
