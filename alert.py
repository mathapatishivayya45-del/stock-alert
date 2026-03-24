import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import os
from datetime import datetime

EMAIL = "mathapatishivayya45@gmail.com"
PASSWORD = os.environ.get("EMAIL_PASS")

# ===== FETCH NIFTY =====
data = yf.download("^NSEI", period="5d", interval="5m")

# ===== SAFE CHECK =====
if data.empty or len(data) < 50:
    msg = "❌ Market data not ready"
else:
    # ===== VWAP =====
    data['VWAP'] = (data['Close'] * data['Volume']).cumsum() / data['Volume'].cumsum()

    # ===== RSI =====
    delta = data['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean()
    data['RSI'] = 100 - (100 / (1 + rs))

    # ===== VOLATILITY =====
    data['Return'] = data['Close'].pct_change()
    volatility = data['Return'].rolling(10).std().iloc[-1]

    # ===== VOLUME =====
    data['Vol_Avg'] = data['Volume'].rolling(10).mean()

    latest = data.iloc[-1]
    prev = data.iloc[-2]

    price = float(latest['Close'])
    open_price = float(latest['Open'])
    vwap = float(latest['VWAP'])
    rsi = float(latest['RSI'])
    volume = float(latest['Volume'])
    vol_avg = float(latest['Vol_Avg'])

    high = float(prev['High'])
    low = float(prev['Low'])

    # ===== NEWS (SIMPLE SENTIMENT) =====
    news_bias = "NEUTRAL"
    if rsi > 60:
        news_bias = "BULLISH 🟢"
    elif rsi < 40:
        news_bias = "BEARISH 🔴"

    # ===== SIGNAL =====
    signal = "❌ NO TRADE"
    entry = "-"
    sl = "-"
    target = "-"

    # CALL
    if (price > vwap and rsi > 55 and price > high and volume > vol_avg):
        entry = round(price,2)
        sl = round(price * 0.92,2)
        target = round(price * 1.12,2)
        signal = "📈 BUY CALL"

    # PUT
    elif (price < vwap and rsi < 45 and price < low and volume > vol_avg):
        entry = round(price,2)
        sl = round(price * 0.92,2)
        target = round(price * 1.12,2)
        signal = "📉 BUY PUT"

    # ===== MESSAGE =====
    msg = f"""📊 NIFTY OPTION REPORT

🕒 {datetime.now()}

Price: {price}
VWAP: {round(vwap,1)}
RSI: {round(rsi,1)}
Volatility: {round(volatility,4)}
Volume: {int(volume)}

Market Bias: {news_bias}

Signal: {signal}

Entry: {entry}
Stoploss: {sl}
Target: {target}
"""

# ===== SEND EMAIL =====
message = MIMEText(msg)
message['Subject'] = "🔥 NIFTY OPTION 9:30 SIGNAL"
message['From'] = EMAIL
message['To'] = EMAIL

server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()
server.login(EMAIL, PASSWORD)
server.sendmail(EMAIL, EMAIL, message.as_string())
server.quit()
