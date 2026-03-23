import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import os
from datetime import datetime

EMAIL = "mathapatishivayya45@gmail.com"
PASSWORD = os.environ.get("EMAIL_PASS")

data = yf.download("^NSEI", period="1d", interval="5m")

if data.empty or len(data) < 30:
    msg = "No data"
else:
    # VWAP
    data['VWAP'] = (data['Close'] * data['Volume']).cumsum() / data['Volume'].cumsum()

    # RSI
    delta = data['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean()
    data['RSI'] = 100 - (100 / (1 + rs))

    # Volume avg
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

    signal = "❌ NO TRADE"
    entry = "-"
    sl = "-"
    target = "-"

    # 🔥 STRONG CALL
    if (price > vwap and 
        rsi > 55 and 
        price > high and 
        volume > vol_avg and 
        price > open_price):

        entry = round(price,2)
        sl = round(price * 0.92,2)
        target = round(price * 1.12,2)

        signal = f"""📈 STRONG CALL
Entry: {entry}
SL: {sl}
Target: {target}
RSI: {round(rsi,1)}"""

    # 🔥 STRONG PUT
    elif (price < vwap and 
          rsi < 45 and 
          price < low and 
          volume > vol_avg and 
          price < open_price):

        entry = round(price,2)
        sl = round(price * 0.92,2)
        target = round(price * 1.12,2)

        signal = f"""📉 STRONG PUT
Entry: {entry}
SL: {sl}
Target: {target}
RSI: {round(rsi,1)}"""

    msg = f"""⚡ HIGH ACCURACY OPTION SIGNAL

🕒 {datetime.now()}

Price: {price}
VWAP: {round(vwap,1)}
Volume: {int(volume)}

{signal}
"""

# EMAIL SEND
message = MIMEText(msg)
message['Subject'] = "🔥 High Accuracy Option Signal"
message['From'] = EMAIL
message['To'] = EMAIL

server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()
server.login(EMAIL, PASSWORD)
server.sendmail(EMAIL, EMAIL, message.as_string())
server.quit()
on:
  schedule:
    - cron: '50 3 * * *'   # 9:20 AM IST
  workflow_dispatch:
