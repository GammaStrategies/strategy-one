# Gamma's Strategy One
This initial strategy was developed specifically for larger pools and is based on taking a moving average and deriving Bollinger Bands to create a projected active liquidity range.

View the simulation folder to view the historic behavior of high fee pools on Uniswap.

View the API-endpoint folder to see how we are collecting and deriving Bollinger Bands for the first strategy. This endpoint uses Uniswap v3 subgraph to analize current and historic pricing at a set interval. With the endpoint, the query returns all pools for a given asset and then pricing data with Bollinger Bands for any pair.



## Here is a rendering of the Bollinger Bands for the USDT-ETH pair:

<img width="1200" alt="gamma-strat-one" src="https://user-images.githubusercontent.com/80003108/118528962-f6a06a80-b710-11eb-8999-55fd5b7ce6ee.png">





