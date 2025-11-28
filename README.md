 
# Agentic AI POC

AI-driven stock trading multi-agent system (research & educational prototype). This repository contains the design and framework for a multi-agent architecture that analyzes stocks and produces trade recommendations for backtesting or paper trading.

> Disclaimer: This project is for research and educational purposes only. It is not financial advice and should not be used for live trading without proper compliance, regulatory approvals, and risk oversight.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Data Sources](#data-sources)
- [Models & Techniques](#models--techniques)
- [Backtesting Engine](#backtesting-engine)
- [Engineering & Infrastructure](#engineering--infrastructure)
- [Sample Orchestrator Workflow](#sample-orchestrator-workflow)
- [Example Output Schema](#example-output-schema)
- [Development Milestones](#development-milestones)
- [Risk & Compliance Notes](#risk--compliance-notes)
- [Contributing](#contributing)
- [License](#license)

## Overview

The system is composed of five cooperating agents:

1. Profile Stock Picker
   - Selects ~50 stocks from a larger universe (e.g., S&P 500).
   - Applies filters for liquidity, volatility, sector exposure, and basic fundamentals.
   - Produces a ranked list of candidate stocks.

2. Fundamental Analyst
   - Analyzes financial statements and key ratios.
   - Evaluates revenue growth, margins, cash flows, and earnings trends.
   - Outputs a fundamental strength score and risk flags.

3. News & Sentiment Analyst (Last 60 Days)
   - Ingests financial news, social media, and other text sources.
   - Uses NLP to classify sentiment and extract events.
   - Produces sentiment momentum and event summaries.

4. Founders & Management Analyst
   - Profiles executives and board members, insider trades, and governance signals.
   - Generates a management credibility score and red flags.

5. Orchestrator / Manager
   - Aggregates and normalizes outputs from all agents.
   - Applies weights, portfolio rules, and risk limits.
   - Produces trade recommendations for backtesting or paper trading.

## Architecture

ASCII overview:

```
                     ┌──────────────────────────┐
                     │  Profile Stock Picker    │
                     └──────────┬───────────────┘
                                │ 50 stocks
                                ▼
                   ┌───────────────────────────┐
                   │ Fundamental Analyst Agent │
                   └──────────┬────────────────┘
                              │ fundamentals
                              ▼
        ┌────────────────────────────┐   ┌─────────────────────────────┐
        │ Sentiment & News Agent     │   │ Mgmt/Founders Profile Agent │
        └─────────┬──────────────────┘   └─────────┬───────────────────┘
                  │ sentiment & news               │ mgmt quality
                  ▼                                ▼
                      ┌──────────────────────────┐
                      │   Orchestrator Agent     │
                      └──────────────────────────┘
                               FINAL SIGNALS
```

## Data Sources

- Market Data: IEX, Polygon, Alpaca, Yahoo (prototype)
- Fundamentals: SEC EDGAR, FinancialModelingPrep, Alpha Vantage
- News: NewsAPI, GDELT, RSS feeds
- Social Media: Reddit API, Twitter/X API
- Insider Trading: OpenInsider, SEC Form 4
- Broker APIs: Alpaca, Interactive Brokers (paper/live)

## Models & Techniques

- Rule-based scoring + ML (XGBoost / LightGBM)
- Transformer-based NLP for sentiment analysis
- Time-decayed sentiment aggregation
- Weighted ensemble scoring across agents
- Portfolio rules and risk constraints

## Backtesting Engine

Features:

- Event-driven backtester
- Position tracking
- Transaction costs & slippage
- Benchmark comparison (e.g., SPY)
- Walk-forward validation

Key metrics tracked:

- Annualized return
- Sharpe & Sortino ratios
- Max drawdown
- Win rate
- Turnover

## Engineering & Infrastructure

- Storage: Delta Lake (S3 / GCS / ADLS)
- Processing: Python, PySpark, Databricks
- Orchestration: Airflow / Prefect
- Microservices: FastAPI for each agent
- Model Registry: MLflow
- CI/CD: GitHub Actions
- Secrets: AWS Secrets Manager / HashiCorp Vault

## Sample Orchestrator Workflow

Example pseudocode:

```python
symbols = picker_agent.run()  # top 50 stocks

fund_scores = parallel_call(fundamental_agent, symbols)
news_scores = parallel_call(news_agent, symbols)
mgmt_scores = parallel_call(management_agent, symbols)

combined = aggregate_scores(fund_scores, news_scores, mgmt_scores)
candidates = select_top(combined, n=10)

final_trades = risk_engine.apply(candidates)

backtester.execute(final_trades)  # or paper trade
```

## Example Output Schema

```json
{
  "symbol": "AAPL",
  "picker_score": 0.82,
  "fundamental": { "score": 0.70, "revenue_growth": 0.12 },
  "news": { "score_60d": -0.10, "events": ["supply_chain_issue"] },
  "management": { "score": 0.90, "insider_sells": 2 },
  "final_score": 0.65,
  "confidence": 0.78,
  "rationale": [
    "Strong fundamentals",
    "Temporary negative sentiment"
  ]
}
```

## Development Milestones

- Phase 1 — Data Pipelines & Stock Picker
  - Market + fundamentals ingestion
  - Initial filtering and ranking model

- Phase 2 — Fundamental & Management Agents
  - Ratio computation
  - Insider data pipeline

- Phase 3 — News/Sentiment Agent
  - NLP pipeline
  - Event extraction

- Phase 4 — Orchestrator + Risk Engine
- Phase 5 — Backtesting + Dashboard

## Risk & Compliance Notes

- Strict position sizing rules
- Hard exposure caps & stop losses
- Audit trail for all trade decisions
- Human-readable rationale required
- Must undergo compliance review before any live trading

## Contributing

Contributions, improvements, ideas, and pull requests are welcome. Please open issues for major changes and follow the repository's contribution guidelines.

## License

This project is released under the MIT License (or another license of your choice).

