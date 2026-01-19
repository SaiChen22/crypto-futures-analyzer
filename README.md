# Crypto Futures Analyzer

Automated crypto futures analysis bot that identifies long and short opportunities on Binance Futures. Runs on GitHub Actions and sends alerts via Telegram.

## Features

- **Technical Analysis**: RSI, MACD, EMA crossovers, volume spikes
- **Funding Rate Analysis**: Identifies extreme funding rates as contrarian signals
- **Liquidation Detection**: Monitors large liquidation events
- **Signal Aggregation**: Combines all signals into a unified score (0-10)
- **Telegram Notifications**: Formatted alerts with actionable insights
- **GitHub Actions**: Automated runs every 15 minutes (free tier friendly)

## Signal Logic

### Long Signals (Bullish)
- RSI < 30 (oversold)
- MACD bullish crossover
- Extreme negative funding rate (shorts paying longs)
- Large long liquidations (potential capitulation)

### Short Signals (Bearish)
- RSI > 70 (overbought)
- MACD bearish crossover
- Extreme positive funding rate (longs paying shorts)
- Large short liquidations (short squeeze exhaustion)

## Quick Start

### 1. Fork this Repository

Click "Fork" to create your own copy of this repository.

### 2. Get API Keys

#### Binance API
1. Go to [Binance API Management](https://www.binance.com/en/my/settings/api-management)
2. Create a new API key
3. Enable "Read" permissions only (no trading needed)
4. Save your API Key and Secret

#### Telegram Bot
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the prompts
3. Save the bot token
4. Start a chat with your bot
5. Get your chat ID:
   - Send any message to your bot
   - Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Find `"chat":{"id":XXXXXXXX}` - that's your chat ID

### 3. Configure GitHub Secrets

Go to your forked repo's **Settings > Secrets and variables > Actions** and add:

| Secret | Description |
|--------|-------------|
| `BINANCE_API_KEY` | Your Binance API key |
| `BINANCE_API_SECRET` | Your Binance API secret |
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID |

### 4. Enable GitHub Actions

1. Go to **Actions** tab in your repository
2. Click "I understand my workflows, go ahead and enable them"
3. The bot will now run every 15 minutes automatically

### 5. Test Manually

1. Go to **Actions** tab
2. Select "Crypto Futures Analysis" workflow
3. Click "Run workflow" to test

## Configuration

### Optional Variables

You can customize behavior using GitHub Variables (**Settings > Secrets and variables > Actions > Variables**):

| Variable | Default | Description |
|----------|---------|-------------|
| `TIMEFRAMES` | `1h,4h` | Comma-separated timeframes to analyze |
| `TOP_COINS_COUNT` | `20` | Number of top coins by volume to analyze |
| `MIN_SIGNAL_SCORE` | `7.0` | Minimum score (0-10) to trigger alerts |

### Adjusting Schedule

Edit `.github/workflows/analyze.yml` to change the schedule:

```yaml
schedule:
  # Every 15 minutes
  - cron: '*/15 * * * *'
  
  # Every 30 minutes
  - cron: '*/30 * * * *'
  
  # Every hour
  - cron: '0 * * * *'
  
  # Every 4 hours
  - cron: '0 */4 * * *'
```

## Alert Format

### Summary Alert
```
Crypto Futures Analysis Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━

LONG Opportunities:
  1. ETHUSDT - Score: 8.5/10 ⭐⭐⭐⭐
      └ Technical: LONG (RSI: 28.5, MACD: bullish)
  2. SOLUSDT - Score: 7.2/10 ⭐⭐⭐
      └ Funding: EXTREME negative (-0.15%)

SHORT Opportunities:
  1. BTCUSDT - Score: 7.8/10 ⭐⭐⭐
      └ Technical: SHORT (RSI: 75.2, MACD: bearish)

━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total signals found: 3
```

### Detailed Alert (for very strong signals)
```
STRONG LONG OPPORTUNITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━

ETHUSDT
Score: 8.5/10 ⭐⭐⭐⭐
Timeframe: 4h

Current Price: $3,245.50

Key Signals:
  ✓ Technical: LONG (RSI: 28.5, MACD: bullish)
  ✓ Funding: EXTREME negative (-0.12%)
  ✓ Good confluence: 2 signals agree

━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ Always do your own research. This is not financial advice.
```

## Local Development

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/crypto-futures-analyzer.git
cd crypto-futures-analyzer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
```

### Run Locally

```bash
# Load environment variables and run
python -m src.main
```

## Project Structure

```
crypto-futures-analyzer/
├── .github/
│   └── workflows/
│       └── analyze.yml         # GitHub Actions workflow
├── src/
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   ├── config.py               # Configuration management
│   ├── exchanges/
│   │   ├── __init__.py
│   │   └── binance.py          # Binance Futures API client
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── technical.py        # RSI, MACD, EMA analysis
│   │   ├── funding.py          # Funding rate analysis
│   │   ├── liquidation.py      # Liquidation analysis
│   │   └── signals.py          # Signal aggregation
│   └── notifications/
│       ├── __init__.py
│       └── telegram.py         # Telegram bot
├── requirements.txt
├── .env.example
└── README.md
```

## GitHub Actions Limits

### Free Tier
- **Public repos**: Unlimited minutes
- **Private repos**: 2,000 minutes/month

### Usage Calculation
- Each run: ~1-2 minutes
- Every 15 min = 96 runs/day = ~144 minutes/day
- Monthly: ~4,320 minutes (exceeds private limit)

**Recommendation**: Use a **public repository** for unlimited free runs, or adjust schedule to every 30-60 minutes for private repos.

## Disclaimer

This tool is for educational and informational purposes only. It is NOT financial advice. Always:

- Do your own research (DYOR)
- Never invest more than you can afford to lose
- Understand that past performance doesn't guarantee future results
- Consider the high risks of futures trading

## License

MIT License - see LICENSE file for details.
