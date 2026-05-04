SELECT symbol, date, adjClose
FROM {schema}.bronze_historical_prices
WHERE symbol IN ('SPY', 'AGG')
  AND date >= DATEADD(DAY, -90, CURRENT_DATE)
ORDER BY date
