# AlgoTrading

Crypto algorithmic trading bot using [Freqtrade](https://www.freqtrade.io/) on Binance.

## Stack
- **Bot**: Freqtrade (Docker)
- **Exchange**: Binance (spot)
- **Strategy**: RSI + EMA trend filter
- **Base currency**: USDT

## Quick start

### 1. Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### 2. Run in dry-run (paper trading)
```bash
docker compose up -d
```

Open the web UI: http://localhost:8080  
Login: `freqtrade` / `change-this-password`

### 3. Backtest before going live
```bash
# Download historical data first
docker compose run --rm freqtrade download-data \
  --config /freqtrade/user_data/config.json \
  --days 90 \
  --timeframe 5m

# Run backtest
docker compose run --rm freqtrade backtesting \
  --config /freqtrade/user_data/config.json \
  --strategy RSIStrategy \
  --timerange 20240101-20240901
```

### 4. Go live (real money)
1. Create Binance API keys with **Spot trading** permission only (no withdrawals)
2. Add keys to `user_data/config.json`:
   ```json
   "key": "your-api-key",
   "secret": "your-api-secret"
   ```
3. Set `"dry_run": false`
4. Restart: `docker compose restart`

## Security
- Never commit API keys — they live only in `user_data/config.json` (gitignored)
- Use API keys with **read + trade** permissions only, never withdrawal permissions
