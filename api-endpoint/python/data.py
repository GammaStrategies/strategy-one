import requests
import datetime
import numpy as np
import pandas as pd

from v3data.utils import timestamp_to_date

FACTORY_ADDRESS = "0x1F98431c8aD98523631AE4a59f267346ea31F984"


class UniV3SubgraphClient:
    def __init__(self):
        self._url = "https://api.thegraph.com/subgraphs/name/ianlapham/uniswap-v3-alt"

    def query(self, query: str, variables=None) -> dict:
        """Make graphql query to subgraph"""
        if variables:
            params = {'query': query, 'variables': variables}
        else:
            params = {'query': query}
        response = requests.post(self._url, json=params)
        return response.json()


class UniV3Data(UniV3SubgraphClient):
    def get_factory(self):
        """Get factory data."""
        query = """
        query factory($id: String!){
          factory(id: $id) {
            id
            poolCount
            txCount
            totalVolumeUSD
            totalValueLockedUSD
          }
        }
        """
        variables = {"id": FACTORY_ADDRESS}
        self.factory = self.query(query, variables)['data']['factory']

    def get_pools(self):
        """Get latest factory data."""
        query = """
        query allPools($skip: Int!) {
          pools(
            first: 1000
            skip: $skip
            orderBy: volumeUSD
            orderDirection: desc
          ){
            id
            token0{
              symbol
            }
            token1{
              symbol
            }
            volumeUSD
          }
        }
        """

        self.get_factory()
        n_skips = int(self.factory['poolCount']) // 1000 + 1

        self.pools = []
        for i in range(n_skips):
            variables = {'skip': i * 1000}
            self.pools.extend(self.query(query, variables)['data']['pools'])

    def get_daily_uniswap_data(self):
        """Get aggregated daily data for uniswap v3."""
        query = """
        {
          uniswapDayDatas(
            first: 1000
            orderBy: date
            orderDirection: asc
          ) {
            id
            date
            volumeUSD
            tvlUSD
            txCount
          }
        }
        """

        self.daily_uniswap_data = self.query(query)['data']['uniswapDayDatas']

    def get_daily_pool_data(self):
        """Get daily data for pools."""

        query = """
        query allDailyPoolData($date: Int!, $skip: Int!){
          poolDayDatas(
            first: 1000
            skip: $skip
            where: { date: $date }
            orderBy: volumeUSD
            orderDirection: desc
          ){
            id
            date
            pool{
              id
              token0{symbol}
              token1{symbol}
            }
            tvlUSD
            volumeUSD
            txCount
          }
        }
        """

        self.get_daily_uniswap_data()
        self.get_factory()
        n_skips = int(self.factory['poolCount']) // 1000 + 1
        # Loop through days
        self.daily_pool_data = []
        for day in self.daily_uniswap_data:
            for i in range(n_skips):
                print(day['date'])
                variables = {"date": day['date'], "skip": i * 1000}
                self.daily_pool_data.extend((self.query(query, variables))['data']['poolDayDatas'])

    def uniswap_data(self):
        """Current TVL, volume, transaction count."""
        self.get_factory()
        data = {
            'totalValueLockedUSD': self.factory['totalValueLockedUSD'],
            'totalVolumeUSD': self.factory['totalVolumeUSD'],
            'txCount': self.factory['txCount']
        }
        return data

    def volume_pie_chart_data(self):
        """Data for pie chart of pool volumes"""
        self.get_pools()

        volume = [float(pool['volumeUSD']) for pool in self.pools]
        labels = [f"{pool['token0']['symbol']}-{pool['token1']['symbol']}" for pool in self.pools]

        data = {
            "datasets": [{
                "data": volume
            }],
            "labels": labels
        }

        return data

    def daily_volume_by_pair(self):
        """Daily volume by pair"""
        self.get_daily_pool_data()
        data = [
            {
                'pair': f"{pool_day['pool']['token0']['symbol']}-{pool_day['pool']['token1']['symbol']}",
                'date': timestamp_to_date(pool_day['date']),
                'volumeUSD': pool_day['volumeUSD']
            }
            for pool_day in self.daily_pool_data if pool_day['volumeUSD'] != '0'
        ]

        return data

    def cumulative_trade_volume(self):
        """Daily cumulative trade volume."""
        self.get_daily_uniswap_data()
        # This assumes data is ordered already
        cumulative = []
        cumulativeVolumeUSD = 0
        for uniswap_day in self.daily_uniswap_data:
            cumulativeVolumeUSD += float(uniswap_day['volumeUSD'])
            cumulative.append(
                {
                    "date": timestamp_to_date(uniswap_day['date']),
                    "cumulativeVolumeUSD": cumulativeVolumeUSD
                }
            )

        return cumulative

    def get_historical_pool_prices(self, pool_address, time_delta):
        query = """
            query poolPrices($id: String!, $timestamp_start: Int!){
                pool(
                    id: $id
                ){
                    swaps(
                        first: 1000
                        orderBy: timestamp
                        orderDirection: asc
                        where: { timestamp_gte: $timestamp_start }
                    ){
                        id
                        timestamp
                        amount0
                        amount1
                    }
                }
            }
        """
        variables = {
            'id': pool_address,
            "timestamp_start": int((datetime.datetime.utcnow() - time_delta).replace(
                tzinfo=datetime.timezone.utc).timestamp())
        }
        has_data = True
        all_swaps = []
        while has_data:
            swaps = self.query(query, variables)['data']['pool']['swaps']

            all_swaps.extend(swaps)
            timestamps = set([int(swap['timestamp']) for swap in swaps])
            variables['timestamp_start'] = max(timestamps)

            if len(swaps) < 1000:
                has_data = False

        df_swaps = pd.DataFrame(all_swaps, dtype=np.float64)
        df_swaps.timestamp = df_swaps.timestamp.astype(np.int64)
        df_swaps.drop_duplicates(inplace=True)
        df_swaps['priceInToken1'] = abs(df_swaps.amount1 / df_swaps.amount0)
        data = df_swaps.to_dict('records')

        return data

    def bollinger_bands(self, pool_address, hours_ago):
        data = self.get_historical_pool_prices(pool_address, datetime.timedelta(hours=hours_ago))
        df = pd.DataFrame(data, dtype=np.float64)
        df['datetime'] = pd.to_datetime(df.timestamp, unit='s')

        interval = hours_ago / 20
        df_closing_price = df.sort_values('datetime').resample(f"{interval}H", on='datetime').last()
        mid = df_closing_price.priceInToken1.mean()
        two_std = 2 * df_closing_price.priceInToken1.std()

        results = {
            'pool': pool_address,
            'period_hours': hours_ago,
            'interval_hours': interval,
            'dt_latest': df.datetime.iat[-1].isoformat(),
            'latest': df.priceInToken1.iat[-1],
            'mid': mid,
            'upper': mid + two_std,
            'lower': mid - two_std
        }

        return results
