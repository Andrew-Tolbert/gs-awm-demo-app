SELECT asset_class, SUM(market_value) AS market_value
FROM {schema}.holdings
GROUP BY asset_class
ORDER BY market_value DESC
