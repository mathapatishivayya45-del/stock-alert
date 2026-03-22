import yfinance as yf
import pandas as pd
import os
import smtplib

stock = "HINDUNILVR.NS"

data = yf.download(stock, period="3mo", interval="1d")

# RSI calculation
delta = data['Close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()

rs = gain / loss
data['RSI'] = 100 - (100 / (1 + rs))

# latest value
latest_rsi = data['RSI'].iloc[-1]
latest_price = data['Close'].iloc[-1]

# signal
if latest_rsi < 30:
    signal = "BUY"
elif latest_rsi > 70:
    signal = "SELL"
else:
    signal = "HOLD"

print("RSI:", latest_rsi)
print("Signal:", signal)

# EMAIL PART
sender = "mathapatishivayya45@gmail.com"
receiver = "mathapatishivayya45@gmail.com"
password = os.environ.get("enit jinx evas ftdp")

message = f"""Subject: Stock Alert

Stock: {stock}
Price: {latest_price}
RSI: {latest_rsi}
Signal: {signal}
"""

try:
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender, password)
    server.sendmail(sender, receiver, message)
    server.quit()
    print("Email sent")

except Exception as e:
    print("Error:", e)
