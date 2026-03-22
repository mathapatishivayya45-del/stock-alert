import yfinance as yf
import pandas as pd
import smtplib
import os

# 📧 Email function
def send_email(message):
    sender = "mathapatishivayya45@gmail.com"
    receiver = "mathapatishivayya45@gmail.com"

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender, os.environ['enit jinx evas ftdp '])

    subject = "🔥 SMART STOCK ALERT 🔥"
    msg = f"Subject: {subject}\n\n{message}"

    server.sendmail(sender, receiver, msg)
    server.quit()

# 📊 RSI
def calculate_rsi(data, period=14):
    delta = data['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# 🧠 Stock list
stocks = [
    "RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS",
    "ICICIBANK.NS","KOTAKBANK.NS","SBIN.NS",
    "HINDUNILVR.NS","ITC.NS","BHARTIARTL.NS",
    "AXISBANK.NS","BAJFINANCE.NS","MARUTI.NS",
    "SUNPHARMA.NS","TITAN.NS","WIPRO.NS"
]

signals = []

for stock in stocks:
    print("Checking:", stock)

    data = yf.download(stock, period="3mo")

    if data.empty:
        continue

    # Indicators
    data['RSI'] = calculate_rsi(data)
    data['50DMA'] = data['Close'].rolling(50).mean()
    data['Volume_Avg'] = data['Volume'].rolling(10).mean()

    latest = data.iloc[-1]

    rsi = latest['RSI']
    price = latest['Close']
    dma = latest['50DMA']
    vol = latest['Volume']
    vol_avg = latest['Volume_Avg']

    print(stock, rsi)

    # 🎯 Smart conditions
    if (rsi < 30) and (price > dma) and (vol > vol_avg):

        entry = round(price,2)
        stoploss = round(price * 0.97,2)
        target = round(price * 1.05,2)

        signals.append(
            f"{stock}\nPrice: {entry}\nRSI: {round(rsi,2)}\nSL: {stoploss}\nTarget: {target}\n"
        )

# 📧 Final message
if signals:
    message = "🔥 STRONG BUY SIGNALS 🔥\n\n" + "\n".join(signals)
else:
    message = "❌ No strong signals today"

print(message)
send_email(message)
