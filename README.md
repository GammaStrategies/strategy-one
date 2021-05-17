# Gamma's Strategy One
This initial strategy was developed specifically for larger pools and is based on taking a moving average and deriving Bollinger Bands to create a projected active liquidity range.

View the simulation folder to view the historic behavior of high fee pools on Uniswap.

View the API-endpoint folder to see how we are collecting and deriving bollinger bands for the first strategy. This endpoint uses Uniswap v3 subgraph to analize current and historic pricing at a set interval. With the endpoint, the query returns all pools for a given asset and then pricing data with bollinger bands for any pair.
