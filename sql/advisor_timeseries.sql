-- Advisor 360: daily portfolio return, benchmark return, and cumulative alpha.
-- Parameters: {schema}, {start_dt}, {end_dt}, {benchmark}
--             {advisor_filter}, {account_filter}, {ticker_filter}
-- Filter clauses are injected as SQL fragments (e.g. "c.advisor_id IN ('A1','A2')" or "1=1").

WITH

-- ── Date range parameters ────────────────────────────────────────────────────
params AS (
  SELECT '{start_dt}' AS start_dt, '{end_dt}' AS end_dt
),

-- ── Nearest trading day on or before each boundary ───────────────────────────
price_dates AS (
  SELECT
    MAX(CASE WHEN date <= (SELECT end_dt   FROM params) THEN date END) AS end_price_dt,
    MAX(CASE WHEN date <= (SELECT start_dt FROM params) THEN date END) AS start_price_dt
  FROM {schema}.bronze_historical_prices
),

-- ── All trading days within the window ───────────────────────────────────────
trading_days AS (
  SELECT DISTINCT date
  FROM {schema}.bronze_historical_prices
  WHERE date >= (SELECT start_price_dt FROM price_dates)
    AND date <= (SELECT end_price_dt   FROM price_dates)
),

-- ── Filtered equity positions (determines portfolio composition) ──────────────
-- Multi-select filters applied here because they affect the portfolio baseline.
filtered_positions AS (
  SELECT t.account_id, t.ticker, SUM(t.quantity) AS quantity, SUM(t.gross_amount) AS total_cost
  FROM {schema}.transactions t
  JOIN {schema}.accounts a ON t.account_id = a.account_id
  JOIN {schema}.clients  c ON a.client_id  = c.client_id
  WHERE t.action IN ('BUY', 'DRIP')
    AND t.ticker != 'CASH'
    AND t.date  <= (SELECT end_dt FROM params)
    AND {advisor_filter}
    AND {account_filter}
    AND {ticker_filter}
  GROUP BY t.account_id, t.ticker
),

-- ── Pre-existing positions (for baseline cost method consistency) ─────────────
pre_existing_positions AS (
  SELECT DISTINCT t.account_id, t.ticker
  FROM {schema}.transactions t
  JOIN {schema}.accounts a ON t.account_id = a.account_id
  JOIN {schema}.clients  c ON a.client_id  = c.client_id
  WHERE t.action IN ('BUY', 'DRIP')
    AND t.ticker != 'CASH'
    AND t.date  <  (SELECT start_dt FROM params)
    AND {advisor_filter}
    AND {account_filter}
),

-- ── Start-of-period prices (for portfolio baseline calculation) ───────────────
series_start_prices AS (
  SELECT symbol, adjClose AS start_price
  FROM {schema}.bronze_historical_prices
  WHERE date = (SELECT start_price_dt FROM price_dates)
),

-- ── Daily mark-to-market portfolio value ─────────────────────────────────────
daily_portfolio AS (
  SELECT td.date, SUM(fp.quantity * hp.adjClose) AS portfolio_value
  FROM trading_days td
  CROSS JOIN filtered_positions fp
  JOIN {schema}.bronze_historical_prices hp ON hp.symbol = fp.ticker AND hp.date = td.date
  GROUP BY td.date
),

-- ── Portfolio cost baseline ───────────────────────────────────────────────────
-- Pre-existing positions use start_price; new positions use actual avg cost paid.
-- This ensures the timeseries % return reconciles with period_pl / period_total_cost_basis.
portfolio_baseline AS (
  SELECT SUM(
    CASE WHEN pp.account_id IS NOT NULL
         THEN fp.quantity * sp.start_price
         ELSE fp.total_cost
    END
  ) AS base
  FROM filtered_positions fp
  LEFT JOIN series_start_prices    sp ON fp.ticker     = sp.symbol
  LEFT JOIN pre_existing_positions pp ON fp.account_id = pp.account_id
                                     AND fp.ticker     = pp.ticker
),

-- ── Daily benchmark close ─────────────────────────────────────────────────────
daily_benchmark AS (
  SELECT td.date, MAX_BY(v.close, v.date) AS benchmark_value
  FROM trading_days td
  LEFT JOIN {schema}.bronze_indexes_and_vix v ON v.index = '{benchmark}' AND v.date = td.date
  GROUP BY td.date
),

-- ── Benchmark value at period start (used as 0% baseline) ────────────────────
benchmark_baseline AS (
  SELECT benchmark_value AS base
  FROM daily_benchmark
  WHERE date = (SELECT start_price_dt FROM price_dates)
),

-- ── Cumulative fees since period start (step function, jumps on fee dates) ────
fees_by_day AS (
  SELECT
    td.date,
    COALESCE(SUM(ABS(f.net_amount)), 0) AS cumulative_fees
  FROM trading_days td
  LEFT JOIN {schema}.transactions f
    ON f.action = 'FEE'
   AND f.date  >= (SELECT start_price_dt FROM price_dates)
   AND f.date  <= td.date
   AND f.account_id IN (SELECT DISTINCT account_id FROM filtered_positions)
  GROUP BY td.date
)

-- ── Final output ──────────────────────────────────────────────────────────────
SELECT
  dp.date,
  ROUND(dp.portfolio_value / NULLIF(pb.base, 0) - 1, 6)                          AS portfolio_return_before_fees,
  ROUND((dp.portfolio_value - fd.cumulative_fees) / NULLIF(pb.base, 0) - 1, 6)   AS portfolio_return_after_fees,
  ROUND((dp.portfolio_value - fd.cumulative_fees) / NULLIF(pb.base, 0) - 1, 6)
    - ROUND(db.benchmark_value / NULLIF(bb.base, 0) - 1, 6)                      AS portfolio_alpha,
  ROUND(fd.cumulative_fees, 2)                                                    AS cumulative_fees,
  ROUND(db.benchmark_value / NULLIF(bb.base, 0) - 1, 6)                          AS benchmark_return,
  '{benchmark}'                                                                   AS benchmark
FROM daily_portfolio dp
LEFT JOIN daily_benchmark  db ON dp.date = db.date
LEFT JOIN fees_by_day      fd ON dp.date = fd.date
CROSS JOIN portfolio_baseline pb
CROSS JOIN benchmark_baseline bb
ORDER BY dp.date
