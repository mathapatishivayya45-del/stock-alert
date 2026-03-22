import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import os

# 📌 EMAIL
sender = "mathapatishivayya45@gmail.com"
receiver = "mathapatishivayya45@gmail.com"
password = os.environ.get("EMAIL_PASS")

# 📌 INDEX (NIFTY)
symbol = "^NSEI"

data = yf.download(symbol, period="5d", interval="5m")

# 📊 INDICATORS
data['50DMA'] = data['Close'].rolling(50).mean()

delta = data['Close'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)

avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()

rs = avg_gain / avg_loss
data['RSI'] = 100 - (100 / (1 + rs))

# 📌 LAST VALUE
latest = data.iloc[-1]

rsi = latest['RSI']
price = latest['Close']
dma = latest['50DMA']

signal = ""

# 🎯 SIGNAL LOGIC
if pd.notna(rsi) and pd.notna(dma):

    if rsi < 30 and price > dma:
        signal = f"📈 BUY CALL\nPrice: {round(price,2)}\nRSI: {round(rsi,2)}"

    elif rsi > 70 and price < dma:
        signal = f"📉 BUY PUT\nPrice: {round(price,2)}\nRSI: {round(rsi,2)}"

    else:
        signal = "❌ No Clear Option Signal"

# 📩 EMAIL
msg = MIMEText(signal)
msg['Subject'] = "⚡ NIFTY Option Signal"
msg['From'] = sender
msg['To'] = receiver

try:
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender, password)
    server.sendmail(sender, receiver, msg.as_string())
    server.quit()
    print("✅ Signal Sent")
except Exception as e:
    print("❌ Error:", e)
