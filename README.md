# NonKYC Telegram Monitor Bot

A Telegram bot for monitoring cryptocurrency prices on NonKYC.io with customizable price alerts.

## Features

- Real-time price monitoring with configurable check interval
- Price change alerts (percentage-based)
- Target price level alerts
- Volume spike detection
- Orderbook depth monitoring
- SQLite storage for user subscriptions
- API key authentication support
- Automatic retry on network errors
- Non-blocking async architecture

## Requirements

- Python 3.10 or higher
- Telegram bot token (from @BotFather)
- NonKYC.io API access (optional for public endpoints)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/nonkyc-telegram-bot.git
cd nonkyc-telegram-bot
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
```

Edit `.env` with your settings:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
NONKYC_API_BASE_URL=https://api.nonkyc.io/api/v2
NONKYC_API_TIMEOUT=10
DATABASE_URL=sqlite:///bot.db
LOG_LEVEL=INFO
LOG_FILE=logs/bot.log
MONITOR_INTERVAL=60
DEFAULT_SYMBOL=XLA/USDT
```

## Usage

Start the bot:
```bash
python main.py
```

To run through Tor (optional):
```bash
torsocks python main.py
```

### Telegram Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Show welcome message | `/start` |
| `/help` | Show command reference | `/help` |
| `/price` | Get current price | `/price XLA/USDT` |
| `/status` | Get market status with orderbook | `/status XLA/USDT` |
| `/subscribe` | Create a new alert | `/subscribe XLA/USDT +5%` |
| `/list` | View your subscriptions | `/list` |
| `/unsubscribe` | Remove a subscription | `/unsubscribe 1` |
| `/toggle` | Enable/disable a subscription | `/toggle 1` |

### Subscription Conditions

Supported condition formats for `/subscribe`:

- Percentage price change: `+5%`, `-3%`
- Target price level: `price=0.15`, `=0.000007`
- Volume spike: `volume+50%`, `vol-30%`
- Orderbook depth: `depth>10000`

Examples:
```
/subscribe XLA/USDT +5%
/subscribe XLA/USDT price=0.000007
/subscribe XLA/USDT volume+50%
```

## Project Structure

```
nonkyc-telegram-bot/
├── main.py              # Application entry point
├── config.py            # Configuration management
├── requirements.txt     # Python dependencies
├── .env.example         # Environment template
├── database/
│   ├── __init__.py
│   └── models.py        # Database models and migrations
├── monitoring/
│   ├── __init__.py
│   ├── client.py        # NonKYC API client
│   └── core.py          # Market monitoring logic
├── notifications/
│   ├── __init__.py
│   └── handler.py       # Telegram notification formatting
└── handlers/
    ├── __init__.py
    └── commands.py      # Telegram command handlers
```

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| TELEGRAM_BOT_TOKEN | (required) | Bot token from @BotFather |
| NONKYC_API_BASE_URL | https://api.nonkyc.io/api/v2 | API base endpoint |
| NONKYC_API_TIMEOUT | 10 | Request timeout in seconds |
| DATABASE_URL | sqlite:///bot.db | Database connection string |
| MONITOR_INTERVAL | 60 | Monitoring check interval in seconds |
| DEFAULT_SYMBOL | XLA/USDT | Default trading pair |
| LOG_LEVEL | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| LOG_FILE | logs/bot.log | Path to log file |

## API Integration

The bot uses the following NonKYC.io API endpoints:

- `GET /api/v2/ticker/{symbol}` — Get market statistics for a single pair
- `GET /api/v2/market/orderbook` — Get orderbook data

Symbol format: Both `XLA/USDT` and `XLA_USDT` are supported.

## Error Handling

- Network errors: Automatic retry with exponential backoff (3 attempts)
- API errors: Logged with details, monitoring continues
- Invalid subscriptions: User receives error message, no crash

## Logging

Logs are written to both console and file (`logs/bot.log` by default).

Log format:
```
2026-04-22 20:49:12,345 [INFO] module.name: Message text
```

Set `LOG_LEVEL=DEBUG` for verbose output during development.

## Security Notes

- Never commit `.env` to version control
- Rotate API tokens if exposed
- Use a dedicated Telegram bot for production
- Consider rate limiting for multi-user deployments

## Development

Install development dependencies:
```bash
pip install black flake8 mypy pytest
```

Code style:
```bash
black .
flake8 .
```

Type checking:
```bash
mypy .
```

## License

MIT License. See LICENSE file for details.

## Disclaimer

This software is provided for informational purposes only. It is not financial advice. Cryptocurrency trading carries significant risk. Use at your own discretion and responsibility.
