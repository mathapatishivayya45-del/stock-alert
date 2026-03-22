import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import os
from datetime import datetime

# 📧 EMAIL SETTINGS
sender = "mathapatishivayya45@gmail.com"
receiver = "mathapatishivayya45@gmail.com"
password = os.environ.get("EMAIL_PASS")

# 📊 STOCK LIST
stocks = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS",
    "ICICIBANK.NS", "SBIN.NS", "ITC.NS", "LT.NS"
]

results = []

for stock in stocks:
    try:
        print(f"Checking: {stock}")

        data = yf.download(stock, period="3mo", interval="1d")

        if data.empty or len(data) < 60:
            continue

        # 📈 INDICATORS
        data['50DMA'] = data['Close'].rolling(50).mean()
        data['200DMA'] = data['Close'].rolling(200).mean()

        delta = data['Close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()

        rs = avg_gain / avg_loss
        data['RSI'] = 100 - (100 / (1 + rs))

        data['Vol_Avg'] = data['Volume'].rolling(10).mean()

        latest = data.iloc[-1]

        rsi = float(latest['RSI'])
        price = float(latest['Close'])
        dma50 = float(latest['50DMA'])
        dma200 = float(latest['200DMA'])
        vol = float(latest['Volume'])
        vol_avg = float(latest['Vol_Avg'])

        # 📊 TREND
        trend = "UPTREND 📈" if price > dma200 else "DOWNTREND 📉"

        # 📌 SIGNAL LOGIC
        signal = "NO SIGNAL ❌"

        if pd.notna(rsi) and pd.notna(dma50) and pd.notna(vol_avg):

            if (rsi < 30) and (price > dma50) and (vol > vol_avg):
                signal = "BUY 🔥"

            elif (rsi > 70) and (price < dma50):
                signal = "SELL ⚠️"

        # 📋 FULL INFO OUTPUT
        result = f"""
🔹 {stock}
Price: ₹{round(price,2)}
RSI: {round(rsi,2)}
50DMA: {round(dma50,2)}
200DMA: {round(dma200,2)}
Volume: {int(vol)}
Avg Vol: {int(vol_avg)}
Trend: {trend}
Signal: {signal}
-------------------------
"""
        results.append(result)

    except Exception as e:
        results.append(f"{stock} ❌ Error: {e}")

# 📩 EMAIL CONTENT
final_message = f"""
📊 STOCK SCANNER REPORT
🕒 {datetime.now()}

{''.join(results)}
"""

msg = MIMEText(final_message)
msg['Subject'] = "🔥 Daily Stock Report"
msg['From'] = sender
msg['To'] = receiver

# 📧 SEND EMAIL
try:
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender, password)
    server.sendmail(sender, receiver, msg.as_string())
    server.quit()
    print("✅ Email Sent Successfully")
except Exception as e:
    print("❌ Email Error:", e)
