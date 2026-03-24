import os
import json
import smtplib
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pytz
import warnings
warnings.filterwarnings('ignore')

IST = pytz.timezone('Asia/Kolkata')

# ============================================================
# 1. NSE DATA FETCHER
# ============================================================
class NSEFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.nseindia.com/',
        }
        self._init_session()

    def _init_session(self):
        try:
            self.session.get('https://www.nseindia.com', headers=self.headers, timeout=10)
        except Exception as e:
            print(f"Session init warning: {e}")

    def get_options_chain(self, symbol="NIFTY"):
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        try:
            resp = self.session.get(url, headers=self.headers, timeout=15)
            data = resp.json()
            return data
        except Exception as e:
            print(f"Options chain error: {e}")
            return None

    def get_nifty_quote(self):
        url = "https://www.nseindia.com/api/allIndices"
        try:
            resp = self.session.get(url, headers=self.headers, timeout=15)
            data = resp.json()
            for item in data.get('data', []):
                if item.get('index') == 'NIFTY 50':
                    return item
        except Exception as e:
            print(f"Quote error: {e}")
        return None

    def get_nifty_historical(self, days=10):
        """Fetch historical NIFTY data from NSE"""
        end_date = datetime.now(IST)
        start_date = end_date - timedelta(days=days)
        url = (
            f"https://www.nseindia.com/api/historical/indicesHistory?"
            f"indexType=NIFTY%2050&from={start_date.strftime('%d-%m-%Y')}&to={end_date.strftime('%d-%m-%Y')}"
        )
        try:
            resp = self.session.get(url, headers=self.headers, timeout=15)
            data = resp.json()
            rows = data.get('data', {}).get('indexCloseOnlineRecords', [])
            df = pd.DataFrame(rows)
            if not df.empty:
                df['date'] = pd.to_datetime(df['EOD_TIMESTAMP'])
                df['close'] = df['EOD_CLOSE_INDEX_VAL'].astype(float)
                df['open'] = df['EOD_OPEN_INDEX_VAL'].astype(float)
                df['high'] = df['EOD_HIGH_INDEX_VAL'].astype(float)
                df['low'] = df['EOD_LOW_INDEX_VAL'].astype(float)
                df = df.sort_values('date').reset_index(drop=True)
            return df
        except Exception as e:
            print(f"Historical data error: {e}")
            return pd.DataFrame()

# ============================================================
# 2. TECHNICAL ANALYSIS
# ============================================================
class TechnicalAnalyzer:
    def __init__(self, df):
        self.df = df.copy()
        self.signals = {}

    def calculate_rsi(self, period=14):
        delta = self.df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        self.df['RSI'] = 100 - (100 / (1 + rs))
        return self.df['RSI'].iloc[-1]

    def calculate_ema(self, period):
        return self.df['close'].ewm(span=period, adjust=False).mean().iloc[-1]

    def calculate_vwap(self):
        # Approx VWAP using daily OHLC
        typical_price = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        vwap = typical_price.mean()
        return vwap

    def support_resistance(self):
        recent = self.df.tail(10)
        support = round(recent['low'].min(), 2)
        resistance = round(recent['high'].max(), 2)
        return support, resistance

    def analyze(self):
        if len(self.df) < 5:
            return {"error": "Not enough data"}

        current_price = self.df['close'].iloc[-1]
        prev_close = self.df['close'].iloc[-2]
        rsi = self.calculate_rsi()
        ema9 = self.calculate_ema(9)
        ema21 = self.calculate_ema(21)
        vwap = self.calculate_vwap()
        support, resistance = self.support_resistance()

        # Trend direction
        trend = "BULLISH" if ema9 > ema21 else "BEARISH"
        price_vs_vwap = "ABOVE VWAP" if current_price > vwap else "BELOW VWAP"

        # RSI signal
        if rsi > 70:
            rsi_signal = "OVERBOUGHT ⚠️"
        elif rsi < 30:
            rsi_signal = "OVERSOLD ✅"
        else:
            rsi_signal = "NEUTRAL"

        # Overall signal
        bull_score = 0
        if ema9 > ema21: bull_score += 1
        if current_price > vwap: bull_score += 1
        if rsi < 60 and rsi > 40: bull_score += 1
        if current_price > prev_close: bull_score += 1

        if bull_score >= 3:
            overall = "BUY CALL"
            emoji = "🟢"
        elif bull_score <= 1:
            overall = "BUY PUT"
            emoji = "🔴"
        else:
            overall = "SIDEWAYS / WAIT"
            emoji = "🟡"

        return {
            "current_price": round(current_price, 2),
            "prev_close": round(prev_close, 2),
            "trend": trend,
            "rsi": round(rsi, 2),
            "rsi_signal": rsi_signal,
            "ema9": round(ema9, 2),
            "ema21": round(ema21, 2),
            "vwap": round(vwap, 2),
            "price_vs_vwap": price_vs_vwap,
            "support": support,
            "resistance": resistance,
            "overall_signal": overall,
            "signal_emoji": emoji,
            "bull_score": bull_score,
        }

# ============================================================
# 3. OPTIONS CHAIN ANALYSIS (LIQUIDITY & OI)
# ============================================================
class OptionsAnalyzer:
    def __init__(self, options_data):
        self.data = options_data

    def analyze(self):
        try:
            records = self.data['records']['data']
            spot_price = self.data['records']['underlyingValue']
            expiry = self.data['records']['expiryDates'][0]  # Nearest expiry

            atm_strike = round(spot_price / 50) * 50  # Round to nearest 50

            call_oi = {}
            put_oi = {}
            call_volume = {}
            put_volume = {}

            for rec in records:
                if rec.get('expiryDate') != expiry:
                    continue
                strike = rec['strikePrice']
                if 'CE' in rec:
                    call_oi[strike] = rec['CE'].get('openInterest', 0)
                    call_volume[strike] = rec['CE'].get('totalTradedVolume', 0)
                if 'PE' in rec:
                    put_oi[strike] = rec['PE'].get('openInterest', 0)
                    put_volume[strike] = rec['PE'].get('totalTradedVolume', 0)

            total_call_oi = sum(call_oi.values())
            total_put_oi = sum(put_oi.values())
            pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0

            # Max Pain (strike with max OI on both sides)
            max_pain_strike = atm_strike
            max_oi_calls = max(call_oi, key=call_oi.get) if call_oi else atm_strike
            max_oi_puts = max(put_oi, key=put_oi.get) if put_oi else atm_strike

            # PCR Interpretation
            if pcr > 1.3:
                pcr_signal = "BULLISH (High Put Writing) 🟢"
            elif pcr < 0.7:
                pcr_signal = "BEARISH (High Call Writing) 🔴"
            else:
                pcr_signal = "NEUTRAL 🟡"

            # ATM CE & PE prices
            atm_ce_price = None
            atm_pe_price = None
            atm_ce_iv = None
            atm_pe_iv = None
            for rec in records:
                if rec.get('expiryDate') == expiry and rec['strikePrice'] == atm_strike:
                    if 'CE' in rec:
                        atm_ce_price = rec['CE'].get('lastPrice')
                        atm_ce_iv = rec['CE'].get('impliedVolatility')
                    if 'PE' in rec:
                        atm_pe_price = rec['PE'].get('lastPrice')
                        atm_pe_iv = rec['PE'].get('impliedVolatility')

            return {
                "spot_price": spot_price,
                "expiry": expiry,
                "atm_strike": atm_strike,
                "pcr": pcr,
                "pcr_signal": pcr_signal,
                "total_call_oi": total_call_oi,
                "total_put_oi": total_put_oi,
                "max_oi_call_strike": max_oi_calls,
                "max_oi_put_strike": max_oi_puts,
                "atm_ce_price": atm_ce_price,
                "atm_pe_price": atm_pe_price,
                "atm_ce_iv": atm_ce_iv,
                "atm_pe_iv": atm_pe_iv,
            }
        except Exception as e:
            print(f"Options analysis error: {e}")
            return {}

# ============================================================
# 4. NEWS FETCHER
# ============================================================
def fetch_market_news():
    news_items = []
    try:
        # Using RSS from MoneyControl / Economic Times
        import feedparser
        feeds = [
            "https://economictimes.indiatimes.com/markets/stocks/rss.cms",
            "https://www.moneycontrol.com/rss/marketreports.xml",
        ]
        for feed_url in feeds:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
                news_items.append({
                    "title": entry.get('title', ''),
                    "summary": entry.get('summary', '')[:150],
                    "link": entry.get('link', ''),
                })
        # Simple sentiment: count bullish/bearish keywords
        bull_kw = ['rally', 'surge', 'gain', 'positive', 'rise', 'up', 'bull', 'growth', 'strong']
        bear_kw = ['fall', 'drop', 'decline', 'negative', 'sell', 'down', 'bear', 'weak', 'crash', 'fear']

        all_text = " ".join([n['title'] + " " + n['summary'] for n in news_items]).lower()
        bull_count = sum(all_text.count(k) for k in bull_kw)
        bear_count = sum(all_text.count(k) for k in bear_kw)

        if bull_count > bear_count + 2:
            sentiment = "BULLISH 🟢"
        elif bear_count > bull_count + 2:
            sentiment = "BEARISH 🔴"
        else:
            sentiment = "NEUTRAL 🟡"

        return {"news": news_items[:6], "sentiment": sentiment, "bull_count": bull_count, "bear_count": bear_count}
    except Exception as e:
        print(f"News error: {e}")
        return {"news": [], "sentiment": "N/A", "bull_count": 0, "bear_count": 0}

# ============================================================
# 5. TRADE SIGNAL GENERATOR
# ============================================================
def generate_trade_signal(tech, options, news):
    signal_score = 0
    reasons = []

    # Technical score
    if tech.get('overall_signal') == "BUY CALL":
        signal_score += 2
        reasons.append("✅ Technical: Bullish (EMA crossover + VWAP)")
    elif tech.get('overall_signal') == "BUY PUT":
        signal_score -= 2
        reasons.append("⚠️ Technical: Bearish (EMA + VWAP breakdown)")

    # PCR score
    pcr = options.get('pcr', 1)
    if pcr > 1.2:
        signal_score += 1
        reasons.append(f"✅ PCR {pcr} - Bullish (Put writers active)")
    elif pcr < 0.8:
        signal_score -= 1
        reasons.append(f"⚠️ PCR {pcr} - Bearish (Call writers active)")

    # News sentiment
    if "BULLISH" in news.get('sentiment', ''):
        signal_score += 1
        reasons.append("✅ News Sentiment: Bullish")
    elif "BEARISH" in news.get('sentiment', ''):
        signal_score -= 1
        reasons.append("⚠️ News Sentiment: Bearish")

    # Final recommendation
    spot = options.get('spot_price', 0)
    atm = options.get('atm_strike', 0)
    support = tech.get('support', 0)
    resistance = tech.get('resistance', 0)

    if signal_score >= 2:
        action = "BUY CALL (CE) 🟢"
        strike_rec = f"{atm} CE"
        entry = options.get('atm_ce_price', 'N/A')
        sl_pct = 0.30
        target_pct = 0.60
        sl = round(entry * (1 - sl_pct), 1) if isinstance(entry, (int, float)) else "N/A"
        target = round(entry * (1 + target_pct), 1) if isinstance(entry, (int, float)) else "N/A"
        index_sl = round(support, 2)
        index_target = round(resistance, 2)
    elif signal_score <= -2:
        action = "BUY PUT (PE) 🔴"
        strike_rec = f"{atm} PE"
        entry = options.get('atm_pe_price', 'N/A')
        sl_pct = 0.30
        target_pct = 0.60
        sl = round(entry * (1 - sl_pct), 1) if isinstance(entry, (int, float)) else "N/A"
        target = round(entry * (1 + target_pct), 1) if isinstance(entry, (int, float)) else "N/A"
        index_sl = round(resistance, 2)
        index_target = round(support, 2)
    else:
        action = "WAIT / NO TRADE 🟡"
        strike_rec = "N/A"
        entry = sl = target = index_sl = index_target = "N/A"

    return {
        "action": action,
        "strike": strike_rec,
        "entry_price": entry,
        "option_sl": sl,
        "option_target": target,
        "index_sl": index_sl,
        "index_target": index_target,
        "score": signal_score,
        "reasons": reasons,
    }

# ============================================================
# 6. EMAIL SENDER
# ============================================================
def send_email(tech, options, news, trade):
    sender = os.environ.get("mathapatishivayya45@gmail.com")
    password = os.environ.get("enit jinx evas ftdp")
    receiver = os.environ.get("mathapatishivayya45@gmail.com", sender)

    now = datetime.now(IST).strftime("%d %b %Y, %I:%M %p IST")

    html = f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 700px; margin: auto; background: #f4f4f4; padding: 20px;">

    <div style="background: #1a1a2e; color: white; padding: 20px; border-radius: 10px; text-align: center;">
        <h1>📈 NIFTY 50 Options Signal</h1>
        <p style="color: #aaa;">{now}</p>
    </div>

    <!-- TRADE SIGNAL -->
    <div style="background: white; margin: 15px 0; padding: 20px; border-radius: 10px; border-left: 5px solid #00b894;">
        <h2>🎯 TODAY'S TRADE SIGNAL</h2>
        <table width="100%" cellpadding="10" style="font-size: 16px;">
            <tr><td><b>Action</b></td><td><b>{trade['action']}</b></td></tr>
            <tr style="background:#f8f9fa;"><td>Strike</td><td>{trade['strike']}</td></tr>
            <tr><td>Entry Price</td><td>₹{trade['entry_price']}</td></tr>
            <tr style="background:#ffe0e0;"><td>Stop Loss (Option)</td><td>₹{trade['option_sl']}</td></tr>
            <tr style="background:#e0ffe0;"><td>Target (Option)</td><td>₹{trade['option_target']}</td></tr>
            <tr style="background:#fff3cd;"><td>NIFTY Index SL</td><td>{trade['index_sl']}</td></tr>
            <tr style="background:#d4edda;"><td>NIFTY Index Target</td><td>{trade['index_target']}</td></tr>
        </table>
        <p><b>Signal Score: {trade['score']}/4</b></p>
        <ul>{''.join(f'<li>{r}</li>' for r in trade['reasons'])}</ul>
    </div>

    <!-- TECHNICAL ANALYSIS -->
    <div style="background: white; margin: 15px 0; padding: 20px; border-radius: 10px; border-left: 5px solid #0984e3;">
        <h2>📊 Technical Analysis</h2>
        <table width="100%" cellpadding="8" style="border-collapse: collapse;">
            <tr style="background:#f1f3f5;"><td>NIFTY Spot</td><td><b>₹{tech.get('current_price', 'N/A')}</b></td></tr>
            <tr><td>Trend (EMA9 vs EMA21)</td><td>{tech.get('trend', 'N/A')}</td></tr>
            <tr style="background:#f1f3f5;"><td>RSI (14)</td><td>{tech.get('rsi', 'N/A')} — {tech.get('rsi_signal', '')}</td></tr>
            <tr><td>VWAP</td><td>{tech.get('vwap', 'N/A')} ({tech.get('price_vs_vwap', '')})</td></tr>
            <tr style="background:#f1f3f5;"><td>EMA 9</td><td>{tech.get('ema9', 'N/A')}</td></tr>
            <tr><td>EMA 21</td><td>{tech.get('ema21', 'N/A')}</td></tr>
            <tr style="background:#f1f3f5;"><td>Support</td><td>{tech.get('support', 'N/A')}</td></tr>
            <tr><td>Resistance</td><td>{tech.get('resistance', 'N/A')}</td></tr>
        </table>
    </div>

    <!-- OPTIONS CHAIN -->
    <div style="background: white; margin: 15px 0; padding: 20px; border-radius: 10px; border-left: 5px solid #6c5ce7;">
        <h2>⚡ Options Chain (Liquidity)</h2>
        <table width="100%" cellpadding="8">
            <tr style="background:#f1f3f5;"><td>Expiry</td><td>{options.get('expiry', 'N/A')}</td></tr>
            <tr><td>ATM Strike</td><td>{options.get('atm_strike', 'N/A')}</td></tr>
            <tr style="background:#f1f3f5;"><td>ATM CE Price</td><td>₹{options.get('atm_ce_price', 'N/A')}</td></tr>
            <tr><td>ATM PE Price</td><td>₹{options.get('atm_pe_price', 'N/A')}</td></tr>
            <tr style="background:#f1f3f5;"><td>ATM CE IV</td><td>{options.get('atm_ce_iv', 'N/A')}%</td></tr>
            <tr><td>ATM PE IV</td><td>{options.get('atm_pe_iv', 'N/A')}%</td></tr>
            <tr style="background:#f1f3f5;"><td>PCR (Put-Call Ratio)</td><td>{options.get('pcr', 'N/A')}</td></tr>
            <tr><td>PCR Signal</td><td>{options.get('pcr_signal', 'N/A')}</td></tr>
            <tr style="background:#f1f3f5;"><td>Max OI Call Strike</td><td>{options.get('max_oi_call_strike', 'N/A')} (Resistance)</td></tr>
            <tr><td>Max OI Put Strike</td><td>{options.get('max_oi_put_strike', 'N/A')} (Support)</td></tr>
        </table>
    </div>

    <!-- NEWS -->
    <div style="background: white; margin: 15px 0; padding: 20px; border-radius: 10px; border-left: 5px solid #fdcb6e;">
        <h2>📰 Market News Sentiment: {news.get('sentiment', 'N/A')}</h2>
        {''.join(f"<p>• <a href='{n.get('link','#')}'>{n.get('title','')}</a></p>" for n in news.get('news', []))}
    </div>

    <div style="background: #dfe6e9; padding: 15px; border-radius: 10px; font-size: 12px; color: #636e72; text-align: center;">
        ⚠️ <b>Disclaimer:</b> This is for educational purposes only. Options trading involves risk. 
        Always use proper position sizing and consult your financial advisor. Not SEBI registered advice.
    </div>

    </body></html>
    """

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"📈 NIFTY Options Signal | {now} | {trade['action']}"
    msg['From'] = sender
    msg['To'] = receiver
    msg.attach(MIMEText(html, 'html'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Email failed: {e}")
        raise

# ============================================================
# 7. MAIN
# ============================================================
def main():
    print("🚀 Starting NIFTY 50 Options Analyzer...")
    
    nse = NSEFetcher()
    
    print("📊 Fetching historical data...")
    hist_df = nse.get_nifty_historical(days=15)
    
    print("⚡ Fetching options chain...")
    options_raw = nse.get_options_chain("NIFTY")
    
    print("📰 Fetching news...")
    news_data = fetch_market_news()

    # Technical Analysis
    tech_data = {}
    if not hist_df.empty:
        ta = TechnicalAnalyzer(hist_df)
        tech_data = ta.analyze()
        print(f"📈 Technical Signal: {tech_data.get('overall_signal')}")
    else:
        print("⚠️ Could not fetch historical data, using defaults")
        tech_data = {"overall_signal": "WAIT", "error": "No data"}

    # Options Analysis
    options_data = {}
    if options_raw:
        oa = OptionsAnalyzer(options_raw)
        options_data = oa.analyze()
        print(f"⚡ PCR: {options_data.get('pcr')} — {options_data.get('pcr_signal')}")
    
    # Generate Trade Signal
    trade_signal = generate_trade_signal(tech_data, options_data, news_data)
    print(f"🎯 Final Signal: {trade_signal['action']}")

    # Send Email
    print("📧 Sending email...")
    send_email(tech_data, options_data, news_data, trade_signal)
    print("✅ Done!")

if __name__ == "__main__":
    main()
