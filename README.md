# Market Session Trading Bot

A comprehensive algorithmic trading bot designed for MT5 brokers with specific support for Exness MT5. The bot trades during different market sessions (Asian, London, New York) using session-specific strategies and robust risk management.

## Features

- **Multi-Currency Trading**: Support for 10+ currency pairs with correlation analysis and risk management
- **Multi-Session Trading**: Automatically trades during Asian, London, and New York sessions
- **Session-Specific Strategies**: Different parameters and approaches for each market session
- **Comprehensive Profit Monitoring**: Real-time P&L tracking, performance metrics, and risk analysis
- **MT5 Integration**: Full support for MetaTrader 5 brokers including Exness
- **Risk Management**: Comprehensive risk controls including position sizing, stop losses, and daily loss limits
- **Real-time Monitoring**: Web dashboard for monitoring bot performance with multi-currency analysis
- **Performance Analytics**: Sharpe ratio, Sortino ratio, Calmar ratio, and Value at Risk calculations
- **Modular Architecture**: Easy to extend with new strategies and indicators
- **Configuration Driven**: YAML-based configuration for easy customization

## Architecture

```
src/
├── core/                 # Core components
│   ├── config.py        # Configuration management
│   ├── session_manager.py # Market session management
│   └── trading_bot.py   # Main trading bot
├── brokers/             # Broker interfaces
│   ├── base_broker.py   # Abstract broker interface
│   └── mt5_broker.py    # MT5 broker implementation
├── strategies/          # Trading strategies
│   ├── base_strategy.py # Base strategy class
│   └── session_breakout_strategy.py # Session breakout strategy
├── risk_management/     # Risk management
│   └── risk_manager.py  # Risk management system
└── dashboard/           # Web dashboard
    └── dashboard.py     # Dash-based monitoring interface
├── core/               # Core components (continued)
│   ├── currency_manager.py # Multi-currency pair management
│   └── profit_monitor.py   # Comprehensive profit monitoring

## Installation

### Prerequisites

- Python 3.8 or higher
- MetaTrader 5 terminal installed
- Exness MT5 account (or other MT5 broker)

### Quick Start

**Option 1: Automated Setup**
```bash
# Run the quick start script
python quick_start.py
```

**Option 2: Multi-Currency Demo**
```bash
# Run the multi-currency demonstration
python multi_currency_example.py
```

**Option 3: Profit Taking Demo**
```bash
# Run the profit taking demonstration
python profit_taking_example.py
```

**Option 3: Manual Setup**

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd ExnessMarketsessionBot
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Create configuration file**:
   ```bash
   python main.py --create-config
   ```

4. **Edit configuration**:
   Edit `config/bot_config.yaml` with your broker credentials and preferences.

## Configuration

### Broker Configuration

```yaml
broker:
  name: "Exness Demo"
  server: "Exness-Demo"  # Your broker server
  login: 12345678        # Your account number
  password: "your_password"
  timeout: 60000
  enable_real_trading: false  # Set to true for live trading
```

### Market Sessions

```yaml
sessions:
  - session_type: "asian"
    start_time: "00:00"
    end_time: "08:00"
    timezone: "UTC"
    enabled: true
  - session_type: "london"
    start_time: "08:00"
    end_time: "16:00"
    timezone: "UTC"
    enabled: true
  - session_type: "new_york"
    start_time: "13:00"
    end_time: "21:00"
    timezone: "UTC"
    enabled: true
```

### Risk Management

```yaml
risk:
  max_position_size: 0.02      # 2% of account per position
  max_daily_loss: 0.05         # 5% daily loss limit
  max_open_positions: 5        # Maximum concurrent positions
  stop_loss_pips: 50.0         # Default stop loss
  take_profit_pips: 100.0      # Default take profit
  trailing_stop: false         # Enable trailing stop
  trailing_stop_pips: 20.0     # Trailing stop distance
```

### Strategies

```yaml
strategies:
  - name: "session_breakout"
    enabled: true
    symbols: ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
    timeframe: "H1"
    parameters:
      breakout_period: 20
      breakout_multiplier: 1.5
      atr_period: 14
      min_volume: 0.01
      max_volume: 1.0
```

## Multi-Currency Trading

The bot supports trading multiple currency pairs simultaneously with intelligent correlation management:

### Supported Currency Pairs

**Major Pairs**:
- EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, NZDUSD

**Minor Pairs**:
- EURGBP, EURJPY, GBPJPY, AUDJPY

### Correlation Management

- **Correlation Analysis**: Real-time correlation matrix calculation
- **Position Limits**: Maximum 3 correlated positions to reduce risk
- **Session Optimization**: Pair selection based on session volatility
- **Risk Distribution**: Automatic position sizing across uncorrelated pairs

### Currency Pair Properties

Each pair includes:
- Session preferences (Asian, London, New York)
- Volatility profiles for each session
- Correlation groups (majors, commodity, crosses)
- Pip values and position size limits
- Spread and commission information

## Time-Based Profit Taking

The bot includes an advanced time-based profit taking system that automatically closes partial positions at predetermined intervals:

### Profit Taking Rules

**Default Rules**:
- **Scalping Quick Profit**: 15 minutes, 10 pips minimum, 50% profit
- **Medium Term Profit**: 1 hour, 20 pips minimum, 70% profit  
- **Session End Profit**: 4 hours, 30 pips minimum, 80% profit
- **Asian Session**: 2 hours, 15 pips minimum, 60% profit
- **London Session**: 90 minutes, 25 pips minimum, 70% profit

### Custom Rule Configuration

```python
from src.core.profit_monitor import ProfitTakingRule

# Create custom profit taking rule
rule = ProfitTakingRule(
    name="Custom Rule",
    enabled=True,
    time_interval_minutes=30,    # Check every 30 minutes
    min_profit_pips=15.0,        # Minimum 15 pips profit
    profit_percentage=0.6,       # Take 60% of profit
    max_trades_per_interval=3,   # Max 3 trades per interval
    session_filter=SessionType.LONDON,  # Only London session
    symbol_filter="EURUSD"       # Only EURUSD
)
```

### Rule Management

```python
# Add custom rule
profit_monitor.add_profit_taking_rule(rule)

# Enable/disable rules
profit_monitor.enable_profit_taking_rule("Custom Rule")
profit_monitor.disable_profit_taking_rule("Custom Rule")

# Remove rule
profit_monitor.remove_profit_taking_rule("Custom Rule")
```

### Profit Taking Features

- **Time Intervals**: Configurable check intervals (1 minute to 24 hours)
- **Profit Thresholds**: Minimum pip profit requirements
- **Partial Closes**: Close percentage of position (10% to 100%)
- **Session Filtering**: Apply rules to specific market sessions
- **Symbol Filtering**: Apply rules to specific currency pairs
- **Rate Limiting**: Maximum trades per interval to prevent over-trading
- **Real-time Monitoring**: Track active positions and profit potential

## Profit Monitoring

Comprehensive profit tracking and performance analysis:

### Real-time Metrics

- **Daily P&L**: Real-time profit/loss tracking
- **Session Performance**: Performance by market session
- **Pair Performance**: Performance by currency pair
- **Risk Metrics**: VaR, drawdown, and risk ratios
- **Profit Taking Status**: Active rules and position monitoring

### Performance Analytics

- **Sharpe Ratio**: Risk-adjusted return measure
- **Sortino Ratio**: Downside risk-adjusted return
- **Calmar Ratio**: Return vs maximum drawdown
- **Profit Factor**: Gross profit vs gross loss
- **Win Rate**: Percentage of profitable trades

### Risk Analysis

- **Value at Risk (VaR)**: 95% confidence interval for potential losses
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Consecutive Losses**: Tracking of losing streaks
- **Daily Loss Limits**: Real-time loss monitoring

### Reporting

Generate comprehensive trading reports:

```bash
# Generate comprehensive report
python main.py --generate-report --save-report

# Generate specific report types
python main.py --generate-report --report-type summary
python main.py --generate-report --report-type risk
```

## Usage

### Basic Usage

1. **Start in demo mode** (recommended for testing):
   ```bash
   python main.py --demo
   ```

2. **Start with custom config**:
   ```bash
   python main.py --config config/my_config.yaml
   ```

3. **Start with debug logging**:
   ```bash
   python main.py --log-level DEBUG
   ```

4. **Start with dashboard**:
   ```bash
   python main.py --dashboard
   ```

### Backtesting

1. **Run backtest**:
   ```bash
   python main.py --backtest
   ```

2. **Custom backtest**:
   ```bash
   python main.py --backtest --backtest-symbol GBPUSD --backtest-days 60
   ```

3. **Test with Exness config**:
   ```bash
   python main.py --config config/exness_config.yaml --backtest
   ```

### Command Line Options

- `--config, -c`: Configuration file path (default: config/bot_config.yaml)
- `--log-level, -l`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `--create-config`: Create default configuration file
- `--demo`: Run in demo mode (paper trading)
- `--backtest`: Run backtest instead of live trading
- `--backtest-symbol`: Symbol for backtesting (default: EURUSD)
- `--backtest-days`: Number of days to backtest (default: 30)
- `--dashboard`: Start the web dashboard
- `--dashboard-host`: Dashboard host (default: localhost)
- `--dashboard-port`: Dashboard port (default: 8050)
- `--generate-report`: Generate a comprehensive trading report
- `--report-type`: Type of report (comprehensive, summary, risk)
- `--save-report`: Save the generated report to file

### Web Dashboard

The bot includes a comprehensive web dashboard for real-time monitoring:

1. **Access the dashboard**: Open http://localhost:8050 in your browser
2. **Monitor performance**: View P&L, positions, and risk metrics
3. **Multi-currency analysis**: View correlation matrix and pair performance
4. **Session performance**: Performance breakdown by market session
5. **Risk metrics**: VaR, drawdown, and risk ratio charts
6. **Generate reports**: Create and download trading reports
7. **Real-time updates**: Auto-refreshing data every 5 seconds

**Dashboard Features**:
- Bot status and connection monitoring
- Performance metrics (win rate, profit factor, Sharpe ratio)
- Daily P&L charts (last 30 days)
- Session performance comparison
- Currency pair performance analysis
- Risk metrics visualization
- Correlation matrix display
- **Profit Taking Status**: Monitor active rules and position profit potential
- Report generation controls

## Trading Strategies

### Session Breakout Strategy

The default strategy trades breakouts during specific market sessions:

- **Asian Session**: Lower volatility, JPY and AUD pairs
- **London Session**: Medium volatility, EUR and GBP pairs  
- **New York Session**: Higher volatility, USD pairs

**Key Features**:
- ATR-based breakout detection
- Session-specific parameters
- Volume confirmation
- Momentum analysis

**Parameters**:
- `breakout_period`: Period for calculating session highs/lows
- `breakout_multiplier`: ATR multiplier for breakout levels
- `atr_period`: Period for Average True Range calculation
- `min_volume`/`max_volume`: Position size limits

### Machine Learning Strategy

Advanced ML-based strategy using Random Forest classifier:

**Key Features**:
- Technical indicator features
- Session-aware predictions
- Confidence-based position sizing
- Automatic model retraining

**Parameters**:
- `lookback_period`: Historical data period for features
- `prediction_threshold`: Minimum confidence for trades
- `retrain_interval`: Model retraining frequency

## Risk Management

The bot includes comprehensive risk management:

### Position Sizing
- Risk-based position sizing using ATR
- Maximum position size as percentage of account
- Broker volume limits enforcement

### Stop Loss & Take Profit
- ATR-based stop loss calculation
- Configurable take profit levels
- Optional trailing stops

### Daily Limits
- Maximum daily loss limit
- Maximum number of open positions
- Automatic position closure on limit breach

### Drawdown Protection
- Maximum drawdown monitoring
- Automatic shutdown on excessive drawdown
- Real-time risk alerts

## Exness MT5 Integration

The bot is specifically optimized for Exness MT5:

### Server Configuration
- Demo: `Exness-Demo`
- Live: `Exness-Live`

### Symbol Support
- Major forex pairs
- Minor forex pairs
- Exotic pairs (with caution)

### Account Types
- Standard accounts
- Pro accounts
- Raw spread accounts

## Development

### Adding New Strategies

1. **Create strategy class**:
   ```python
   from src.strategies.base_strategy import BaseStrategy
   
   class MyStrategy(BaseStrategy):
       def calculate_indicators(self, data):
           # Calculate your indicators
           pass
       
       def generate_signals(self, data):
           # Generate trading signals
           pass
       
       def should_trade(self, symbol, session_type):
           # Define when to trade
           pass
   ```

2. **Register in trading bot**:
   ```python
   # In trading_bot.py
   if strategy_config.name == "my_strategy":
       strategy = MyStrategy(strategy_config, self.broker, 
                           self.risk_manager, self.session_manager)
   ```

### Adding New Indicators

Create indicator functions in `src/indicators/`:

```python
def my_indicator(data, period=14):
    """Calculate custom indicator."""
    return data['close'].rolling(window=period).mean()
```

### Testing

Run tests with pytest:
```bash
pytest tests/
```

## Monitoring & Logging

### Log Files
- Location: `logs/trading_bot.log`
- Rotation: Daily
- Retention: 30 days
- Compression: ZIP

### Log Levels
- `DEBUG`: Detailed debugging information
- `INFO`: General information
- `WARNING`: Warning messages
- `ERROR`: Error messages

### Performance Metrics
- Total trades and win rate
- P&L tracking
- Drawdown analysis
- Session performance

## Troubleshooting

### Common Issues

1. **MT5 Connection Failed**:
   - Verify MT5 terminal is running
   - Check server name and credentials
   - Ensure firewall allows MT5 connection

2. **No Trading Signals**:
   - Check if market sessions are active
   - Verify strategy parameters
   - Review market data availability

3. **Risk Limits Hit**:
   - Review risk configuration
   - Check account balance
   - Monitor position sizes

### Debug Mode

Enable debug logging for detailed information:
```bash
python main.py --log-level DEBUG
```

## Safety & Disclaimer

⚠️ **Important**: This bot is for educational and research purposes. Trading involves substantial risk of loss.

### Safety Features
- Demo mode by default
- Comprehensive risk management
- Daily loss limits
- Position size controls

### Recommendations
- Always test in demo mode first
- Start with small position sizes
- Monitor the bot regularly
- Understand the strategies before live trading

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Check the documentation
- Review the logs
- Test in demo mode first
- Start with conservative settings

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

---

**Happy Trading! 📈** 