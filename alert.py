import yfinance as yf
import pandas as pd
import smtplib
from email.message import EmailMessage
import os

# EMAIL CONFIG
sender = "mathapatishivayya45@gmail.com"
receiver = "mathapatishivayya45@gmail.com"
password = os.getenv("enit jinx evas ftdp")

# STOCK LIST
stocks = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS"]

results = []

for stock in stocks:
    data = yf.download(stock, period="3mo", interval="1d", progress=False)

    if data.empty:
        continue

    data['MA20'] = data['Close'].rolling(20).mean()

    delta = data['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss
    data['RSI'] = 100 - (100 / (1 + rs))

    latest = data.iloc[-1]

    if latest['RSI'] < 30:
        signal = "BUY"
    elif latest['RSI'] > 70:
        signal = "SELL"
    else:
        signal = "HOLD"

    results.append(f"{stock} → {signal} | RSI: {round(latest['RSI'],2)}")

# EMAIL SEND
msg = EmailMessage()
msg.set_content("\n".join(results))
msg['Subject'] = "Stock Alert"
msg['From'] = sender
msg['To'] = receiver

with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
    smtp.login(sender, password)
    smtp.send_message(msg)
