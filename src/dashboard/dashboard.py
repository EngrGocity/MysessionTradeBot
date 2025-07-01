"""
Web dashboard for the Market Session Trading Bot.
"""

import dash
from dash import dcc, html, Input, Output, callback_context
import plotly.graph_objs as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Any, Optional
import threading
import time

logger = logging.getLogger(__name__)

class TradingDashboard:
    """
    Web dashboard for monitoring trading bot performance.
    """
    
    def __init__(self, trading_bot=None, host='localhost', port=8050):
        """
        Initialize the dashboard.
        
        Args:
            trading_bot: Trading bot instance
            host: Dashboard host
            port: Dashboard port
        """
        self.trading_bot = trading_bot
        self.host = host
        self.port = port
        self.app = None
        self.data_cache = {}
        self.update_interval = 5  # seconds
        
    def create_app(self):
        """Create the Dash application."""
        self.app = dash.Dash(__name__, title="Trading Bot Dashboard")
        
        # Layout
        self.app.layout = html.Div([
            # Header
            html.H1("Market Session Trading Bot Dashboard", 
                   style={'textAlign': 'center', 'color': '#2c3e50'}),
            
            # Status indicators
            html.Div([
                html.Div([
                    html.H3("Bot Status", style={'color': '#2c3e50'}),
                    html.Div(id='bot-status', style={'fontSize': '18px', 'fontWeight': 'bold'})
                ], style={'width': '25%', 'display': 'inline-block'}),
                
                html.Div([
                    html.H3("Connection", style={'color': '#2c3e50'}),
                    html.Div(id='connection-status', style={'fontSize': '18px', 'fontWeight': 'bold'})
                ], style={'width': '25%', 'display': 'inline-block'}),
                
                html.Div([
                    html.H3("Daily P&L", style={'color': '#2c3e50'}),
                    html.Div(id='daily-pnl', style={'fontSize': '18px', 'fontWeight': 'bold'})
                ], style={'width': '25%', 'display': 'inline-block'}),
                
                html.Div([
                    html.H3("Open Positions", style={'color': '#2c3e50'}),
                    html.Div(id='open-positions', style={'fontSize': '18px', 'fontWeight': 'bold'})
                ], style={'width': '25%', 'display': 'inline-block'})
            ], style={'marginBottom': '20px'}),
            
            # Main content tabs
            dcc.Tabs([
                # Overview tab
                dcc.Tab(label='Overview', children=[
                    html.Div([
                        # Performance metrics
                        html.Div([
                            html.H3("Performance Metrics", style={'color': '#2c3e50'}),
                            html.Div(id='performance-metrics', style={'fontSize': '14px'})
                        ], style={'width': '50%', 'display': 'inline-block', 'verticalAlign': 'top'}),
                        
                        # Risk metrics
                        html.Div([
                            html.H3("Risk Metrics", style={'color': '#2c3e50'}),
                            html.Div(id='risk-metrics', style={'fontSize': '14px'})
                        ], style={'width': '50%', 'display': 'inline-block', 'verticalAlign': 'top'})
                    ]),
                    
                    # Charts
                    html.Div([
                        dcc.Graph(id='daily-pnl-chart'),
                        dcc.Graph(id='session-performance-chart')
                    ])
                ]),
                
                # Positions tab
                dcc.Tab(label='Positions', children=[
                    html.Div([
                        html.H3("Open Positions", style={'color': '#2c3e50'}),
                        html.Div(id='positions-table')
                    ]),
                    
                    html.Div([
                        html.H3("Recent Trades", style={'color': '#2c3e50'}),
                        html.Div(id='recent-trades-table')
                    ])
                ]),
                
                # Multi-Currency tab
                dcc.Tab(label='Multi-Currency', children=[
                    html.Div([
                        html.H3("Currency Pair Performance", style={'color': '#2c3e50'}),
                        html.Div(id='pair-performance')
                    ]),
                    
                    html.Div([
                        html.H3("Correlation Matrix", style={'color': '#2c3e50'}),
                        html.Div(id='correlation-matrix', style={'fontFamily': 'monospace'})
                    ])
                ]),
                
                # Profit Taking tab
                dcc.Tab(label='Profit Taking', children=[
                    html.Div([
                        html.H3("Profit Taking Status", style={'color': '#2c3e50'}),
                        html.Div(id='profit-taking-status')
                    ]),
                    
                    html.Div([
                        html.H3("Active Rules", style={'color': '#2c3e50'}),
                        html.Div(id='active-rules')
                    ])
                ]),
                
                # Reports tab
                dcc.Tab(label='Reports', children=[
                    html.Div([
                        html.H3("Generate Reports", style={'color': '#2c3e50'}),
                        html.Button("Generate Summary Report", id='generate-summary-btn', n_clicks=0),
                        html.Button("Generate Risk Report", id='generate-risk-btn', n_clicks=0),
                        html.Button("Generate Full Report", id='generate-full-btn', n_clicks=0),
                        html.Div(id='report-output')
                    ])
                ])
            ]),
            
            # Auto-refresh interval
            dcc.Interval(
                id='interval-component',
                interval=self.update_interval * 1000,  # milliseconds
                n_intervals=0
            )
        ])
        
        # Callbacks
        self._setup_callbacks()
        
    def _setup_callbacks(self):
        """Setup dashboard callbacks."""
        
        @self.app.callback(
            [Output('bot-status', 'children'),
             Output('connection-status', 'children'),
             Output('daily-pnl', 'children'),
             Output('open-positions', 'children')],
            [Input('interval-component', 'n_intervals')]
        )
        def update_status_indicators(n):
            """Update status indicators."""
            try:
                if self.trading_bot is None:
                    return "Not Connected", "Disconnected", "N/A", "N/A"
                
                # Bot status
                bot_status = "Running" if self.trading_bot.is_running else "Stopped"
                bot_color = "green" if self.trading_bot.is_running else "red"
                
                # Connection status
                connection_status = "Connected" if self.trading_bot.broker.is_connected() else "Disconnected"
                connection_color = "green" if self.trading_bot.broker.is_connected() else "red"
                
                # Daily P&L
                daily_pnl = self.trading_bot.profit_monitor.get_daily_pnl()
                pnl_color = "green" if daily_pnl >= 0 else "red"
                
                # Open positions
                open_positions = len(self.trading_bot.broker.get_open_positions())
                
                return [
                    html.Span(bot_status, style={'color': bot_color}),
                    html.Span(connection_status, style={'color': connection_color}),
                    html.Span(f"${daily_pnl:.2f}", style={'color': pnl_color}),
                    html.Span(str(open_positions))
                ]
            except Exception as e:
                logger.error(f"Error updating status indicators: {e}")
                return "Error", "Error", "Error", "Error"
        
        @self.app.callback(
            [Output('performance-metrics', 'children'),
             Output('risk-metrics', 'children')],
            [Input('interval-component', 'n_intervals')]
        )
        def update_metrics(n):
            """Update performance and risk metrics."""
            try:
                if self.trading_bot is None:
                    return "No data available", "No data available"
                
                # Performance metrics
                metrics = self.trading_bot.profit_monitor.get_performance_metrics()
                perf_text = self._format_performance_metrics(metrics)
                
                # Risk metrics
                risk_data = self.trading_bot.risk_manager.get_risk_metrics()
                risk_text = self._format_risk_metrics(risk_data)
                
                return perf_text, risk_text
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
                return "Error loading metrics", "Error loading metrics"
        
        @self.app.callback(
            Output('daily-pnl-chart', 'figure'),
            [Input('interval-component', 'n_intervals')]
        )
        def update_daily_pnl_chart(n):
            """Update daily P&L chart."""
            try:
                if self.trading_bot is None:
                    return self._create_empty_chart("No data available")
                
                # Get daily P&L data
                daily_data = self.trading_bot.profit_monitor.get_daily_pnl_history(days=30)
                
                if not daily_data:
                    return self._create_empty_chart("No P&L data available")
                
                # Create chart
                dates = [d['date'] for d in daily_data]
                pnl_values = [d['pnl'] for d in daily_data]
                cumulative_pnl = np.cumsum(pnl_values)
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=cumulative_pnl,
                    mode='lines+markers',
                    name='Cumulative P&L',
                    line=dict(color='#3498db', width=2),
                    marker=dict(size=6)
                ))
                
                fig.update_layout(
                    title="Daily P&L (Last 30 Days)",
                    xaxis_title="Date",
                    yaxis_title="Cumulative P&L ($)",
                    height=400,
                    showlegend=True
                )
                
                return fig
            except Exception as e:
                logger.error(f"Error updating daily P&L chart: {e}")
                return self._create_empty_chart("Error loading chart")
        
        @self.app.callback(
            Output('session-performance-chart', 'figure'),
            [Input('interval-component', 'n_intervals')]
        )
        def update_session_chart(n):
            """Update session performance chart."""
            try:
                if self.trading_bot is None:
                    return self._create_empty_chart("No data available")
                
                # Get session performance data
                session_data = self.trading_bot.profit_monitor.get_session_performance()
                
                if not session_data:
                    return self._create_empty_chart("No session data available")
                
                # Create chart
                sessions = list(session_data.keys())
                profits = [session_data[s].get('profit', 0) for s in sessions]
                trades = [session_data[s].get('trades', 0) for s in sessions]
                
                fig = make_subplots(
                    rows=1, cols=2,
                    subplot_titles=('Session P&L', 'Session Trades'),
                    specs=[[{"type": "bar"}, {"type": "bar"}]]
                )
                
                fig.add_trace(
                    go.Bar(x=sessions, y=profits, name='P&L', marker_color='#2ecc71'),
                    row=1, col=1
                )
                
                fig.add_trace(
                    go.Bar(x=sessions, y=trades, name='Trades', marker_color='#e74c3c'),
                    row=1, col=2
                )
                
                fig.update_layout(
                    title="Session Performance",
                    height=400,
                    showlegend=True
                )
                
                return fig
            except Exception as e:
                logger.error(f"Error updating session chart: {e}")
                return self._create_empty_chart("Error loading chart")
        
        @self.app.callback(
            [Output('positions-table', 'children'),
             Output('recent-trades-table', 'children')],
            [Input('interval-component', 'n_intervals')]
        )
        def update_positions_and_trades(n):
            """Update positions and trades tables."""
            try:
                if self.trading_bot is None:
                    return "No data available", "No data available"
                
                # Open positions
                positions = self.trading_bot.broker.get_open_positions()
                positions_table = self._create_positions_table(positions)
                
                # Recent trades
                trades = self.trading_bot.broker.get_recent_trades(limit=10)
                trades_table = self._create_trades_table(trades)
                
                return positions_table, trades_table
            except Exception as e:
                logger.error(f"Error updating positions and trades: {e}")
                return "Error loading data", "Error loading data"
        
        @self.app.callback(
            [Output('pair-performance', 'children'),
             Output('correlation-matrix', 'children')],
            [Input('interval-component', 'n_intervals')]
        )
        def update_multi_currency(n):
            """Update multi-currency data."""
            try:
                if self.trading_bot is None:
                    return "No data available", "No data available"
                
                # Pair performance
                pair_data = self.trading_bot.profit_monitor.get_pair_performance()
                pair_text = self._format_pair_performance(pair_data)
                
                # Correlation matrix
                correlation_data = self.trading_bot.currency_manager.get_correlation_matrix()
                correlation_text = self._format_correlation_matrix(correlation_data)
                
                return pair_text, correlation_text
            except Exception as e:
                logger.error(f"Error updating multi-currency data: {e}")
                return "Error loading data", "Error loading data"
        
        @self.app.callback(
            [Output('profit-taking-status', 'children'),
             Output('active-rules', 'children')],
            [Input('interval-component', 'n_intervals')]
        )
        def update_profit_taking(n):
            """Update profit taking status."""
            try:
                if self.trading_bot is None:
                    return "No data available", "No data available"
                
                # Profit taking status
                profit_data = self.trading_bot.profit_monitor.get_profit_taking_status()
                status_text = self._format_profit_taking_status(profit_data)
                
                # Active rules
                rules_text = self._format_active_rules(profit_data.get('active_rules', []))
                
                return status_text, rules_text
            except Exception as e:
                logger.error(f"Error updating profit taking data: {e}")
                return "Error loading data", "Error loading data"
        
        @self.app.callback(
            Output('report-output', 'children'),
            [Input('generate-summary-btn', 'n_clicks'),
             Input('generate-risk-btn', 'n_clicks'),
             Input('generate-full-btn', 'n_clicks')]
        )
        def generate_reports(summary_clicks, risk_clicks, full_clicks):
            """Generate reports."""
            try:
                if self.trading_bot is None:
                    return "Bot not connected"
                
                ctx = callback_context
                if not ctx.triggered:
                    return ""
                
                button_id = ctx.triggered[0]['prop_id'].split('.')[0]
                
                if button_id == 'generate-summary-btn':
                    report = self.trading_bot.profit_monitor.generate_report('summary')
                    return f"Summary report generated: {report}"
                elif button_id == 'generate-risk-btn':
                    report = self.trading_bot.profit_monitor.generate_report('risk')
                    return f"Risk report generated: {report}"
                elif button_id == 'generate-full-btn':
                    report = self.trading_bot.profit_monitor.generate_report('comprehensive')
                    return f"Full report generated: {report}"
                
                return ""
            except Exception as e:
                logger.error(f"Error generating report: {e}")
                return f"Error generating report: {e}"
    
    def _format_performance_metrics(self, metrics: Dict[str, Any]) -> str:
        """Format performance metrics for display."""
        try:
            lines = []
            
            if 'total_trades' in metrics:
                lines.append(f"Total Trades: {metrics['total_trades']}")
            
            if 'win_rate' in metrics:
                win_rate = metrics['win_rate'] * 100
                lines.append(f"Win Rate: {win_rate:.1f}%")
            
            if 'profit_factor' in metrics:
                lines.append(f"Profit Factor: {metrics['profit_factor']:.2f}")
            
            if 'total_profit' in metrics:
                lines.append(f"Total Profit: ${metrics['total_profit']:.2f}")
            
            if 'sharpe_ratio' in metrics:
                lines.append(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
            
            return "\n".join(lines) if lines else "No performance data"
        except Exception as e:
            logger.error(f"Error formatting performance metrics: {e}")
            return "Error formatting metrics"
    
    def _format_risk_metrics(self, risk_data: Dict[str, Any]) -> str:
        """Format risk metrics for display."""
        try:
            lines = []
            
            if 'current_drawdown' in risk_data:
                lines.append(f"Current Drawdown: {risk_data['current_drawdown']:.2f}%")
            
            if 'max_drawdown' in risk_data:
                lines.append(f"Max Drawdown: {risk_data['max_drawdown']:.2f}%")
            
            if 'var_95' in risk_data:
                lines.append(f"VaR (95%): ${risk_data['var_95']:.2f}")
            
            if 'open_positions' in risk_data:
                lines.append(f"Open Positions: {risk_data['open_positions']}")
            
            return "\n".join(lines) if lines else "No risk data"
        except Exception as e:
            logger.error(f"Error formatting risk metrics: {e}")
            return "Error formatting metrics"
    
    def _create_empty_chart(self, message: str) -> go.Figure:
        """Create an empty chart with a message."""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            height=400
        )
        return fig
    
    def _create_positions_table(self, positions: List[Dict[str, Any]]) -> html.Div:
        """Create positions table."""
        try:
            if not positions:
                return html.Div("No open positions")
            
            headers = ['Symbol', 'Type', 'Volume', 'Open Price', 'Current Price', 'P&L', 'Time']
            
            rows = []
            for pos in positions:
                rows.append(html.Tr([
                    html.Td(pos.get('symbol', 'N/A')),
                    html.Td(pos.get('type', 'N/A')),
                    html.Td(f"{pos.get('volume', 0):.2f}"),
                    html.Td(f"{pos.get('price_open', 0):.5f}"),
                    html.Td(f"{pos.get('price_current', 0):.5f}"),
                    html.Td(f"{pos.get('profit', 0):.2f}", 
                           style={'color': 'green' if pos.get('profit', 0) >= 0 else 'red'}),
                    html.Td(pos.get('time_open', 'N/A'))
                ]))
            
            return html.Table([
                html.Thead(html.Tr([html.Th(h) for h in headers])),
                html.Tbody(rows)
            ], style={'width': '100%', 'border': '1px solid black'})
        except Exception as e:
            logger.error(f"Error creating positions table: {e}")
            return html.Div("Error creating table")
    
    def _create_trades_table(self, trades: List[Dict[str, Any]]) -> html.Div:
        """Create trades table."""
        try:
            if not trades:
                return html.Div("No recent trades")
            
            headers = ['Symbol', 'Type', 'Volume', 'Open Price', 'Close Price', 'P&L', 'Time']
            
            rows = []
            for trade in trades:
                rows.append(html.Tr([
                    html.Td(trade.get('symbol', 'N/A')),
                    html.Td(trade.get('type', 'N/A')),
                    html.Td(f"{trade.get('volume', 0):.2f}"),
                    html.Td(f"{trade.get('price_open', 0):.5f}"),
                    html.Td(f"{trade.get('price_close', 0):.5f}"),
                    html.Td(f"{trade.get('profit', 0):.2f}", 
                           style={'color': 'green' if trade.get('profit', 0) >= 0 else 'red'}),
                    html.Td(trade.get('time_close', 'N/A'))
                ]))
            
            return html.Table([
                html.Thead(html.Tr([html.Th(h) for h in headers])),
                html.Tbody(rows)
            ], style={'width': '100%', 'border': '1px solid black'})
        except Exception as e:
            logger.error(f"Error creating trades table: {e}")
            return html.Div("Error creating table")
    
    def _format_pair_performance(self, pair_data: Dict[str, Any]) -> str:
        """Format pair performance for display."""
        try:
            lines = []
            
            for pair, data in pair_data.items():
                if isinstance(data, dict):
                    profit = data.get('profit', 0)
                    trades = data.get('trades', 0)
                    win_rate = data.get('win_rate', 0) * 100
                    
                    lines.append(f"{pair}: {trades} trades, ${profit:.2f} profit, {win_rate:.1f}% win rate")
            
            return "\n".join(lines) if lines else "No pair data available"
        except Exception as e:
            logger.error(f"Error formatting pair performance: {e}")
            return "Error formatting data"
    
    def _format_correlation_matrix(self, correlation_data: Dict[str, Dict[str, float]]) -> str:
        """Format correlation matrix for display."""
        try:
            if not correlation_data:
                return "No correlation data available"
            
            pairs = list(correlation_data.keys())
            if not pairs:
                return "No correlation data available"
            
            # Create header
            header = "Pair".ljust(10)
            for pair in pairs:
                header += f"{pair}".rjust(8)
            lines = [header]
            lines.append("-" * len(header))
            
            # Create matrix rows
            for pair1 in pairs:
                row = pair1.ljust(10)
                for pair2 in pairs:
                    if pair1 == pair2:
                        correlation = 1.0
                    else:
                        correlation = correlation_data.get(pair1, {}).get(pair2, 0.0)
                    row += f"{correlation:8.3f}"
                lines.append(row)
            
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Error formatting correlation matrix: {e}")
            return "Error formatting matrix"
    
    def _format_profit_taking_status(self, profit_data: Dict[str, Any]) -> str:
        """Format profit taking status for display."""
        try:
            lines = []
            
            # Active positions
            if 'active_positions' in profit_data:
                lines.append("Positions with Profit Potential:")
                for position in profit_data['active_positions']:
                    symbol = position.get('symbol', 'Unknown')
                    profit_pips = position.get('profit_pips', 0)
                    profit_percent = position.get('profit_percent', 0)
                    lines.append(f"  - {symbol}: {profit_pips:.1f} pips ({profit_percent:.1f}%)")
            
            # Recent actions
            if 'recent_actions' in profit_data:
                lines.append("\nRecent Profit Taking Actions:")
                for action in profit_data['recent_actions']:
                    symbol = action.get('symbol', 'Unknown')
                    action_type = action.get('action', 'Unknown')
                    profit = action.get('profit', 0)
                    time = action.get('time', 'Unknown')
                    lines.append(f"  - {time}: {symbol} {action_type} (Profit: ${profit:.2f})")
            
            return "\n".join(lines) if lines else "No profit taking data available"
        except Exception as e:
            logger.error(f"Error formatting profit taking status: {e}")
            return "Error formatting data"
    
    def _format_active_rules(self, rules: List[Dict[str, Any]]) -> str:
        """Format active rules for display."""
        try:
            if not rules:
                return "No active rules"
            
            lines = []
            for rule in rules:
                name = rule.get('name', 'Unknown')
                enabled = "Enabled" if rule.get('enabled', False) else "Disabled"
                interval = rule.get('time_interval_minutes', 0)
                min_profit = rule.get('min_profit_pips', 0)
                profit_percent = rule.get('profit_percentage', 0) * 100
                
                lines.append(f"{name}: {enabled}")
                lines.append(f"  - Check every {interval} minutes")
                lines.append(f"  - Min profit: {min_profit} pips")
                lines.append(f"  - Take {profit_percent:.0f}% of profit")
                lines.append("")
            
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Error formatting active rules: {e}")
            return "Error formatting rules"
    
    def start(self):
        """Start the dashboard server."""
        try:
            if self.app is None:
                self.create_app()
            
            logger.info(f"Starting dashboard on http://{self.host}:{self.port}")
            self.app.run_server(host=self.host, port=self.port, debug=False)
        except Exception as e:
            logger.error(f"Error starting dashboard: {e}")
    
    def stop(self):
        """Stop the dashboard server."""
        try:
            logger.info("Stopping dashboard")
            # Note: Dash doesn't have a built-in stop method
            # The server will stop when the process is terminated
        except Exception as e:
            logger.error(f"Error stopping dashboard: {e}")

def create_dashboard(trading_bot=None, host='localhost', port=8050):
    """
    Create and return a dashboard instance.
    
    Args:
        trading_bot: Trading bot instance
        host: Dashboard host
        port: Dashboard port
    
    Returns:
        TradingDashboard instance
    """
    return TradingDashboard(trading_bot, host, port) 