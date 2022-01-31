# # Load Libraries
import pandas as pd
import numpy as np
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt
import datetime as dt
import re

from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestRegressor
from sklearn import svm
from sklearn.metrics import mean_absolute_error



import os, sys


currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from opensea.database import read_mongo, write_mongo,connect_mongo
from opensea.cryto_prices import update_eth_usd
from opensea.current_listings import update_current_listings
from opensea.opensea_events import update_opensea_events



database = connect_mongo()
db_collections = database.collection_names(include_system_collections=False)
sales_regex = re.compile('.*_sales')
sales_collections = list(filter(sales_regex.match, db_collections))
collection_with_sales = [re.sub('_sales','',i) for i in sales_collections]

traits_regex = re.compile('.*_traits')
traits_collections = list(filter(traits_regex.match, db_collections))
collection_with_traits = [re.sub('_traits','',i) for i in traits_collections]

collections = list(set.intersection(set(collection_with_sales),set(collection_with_traits)))


sales = pd.DataFrame()
traits = pd.DataFrame()
rarity_col_regex = re.compile('.*_rarity')
for x in collections:
    update_opensea_events(x,eventTypes=["sales"])
    print(f'getting data for {x}')
    sales_x = read_mongo(f"{x}_sales",query_projection=['asset_id','collection','time','sale_currency','sale_price'])
    sales = sales.append(sales_x)
    traits_x = read_mongo(f"{x}_traits",return_df=True)
    rarity_cols = list(filter(rarity_col_regex.match, traits_x.columns))
    rarity_cols.remove('factoral_rarity')
    traits_x['collection'] = x
    traits_x['mean_rarity'] = traits_x[rarity_cols].mean(axis=1)
    traits_x['min_rarity'] = traits_x[rarity_cols].min(axis=1)
    traits_x['max_rarity'] = traits_x[rarity_cols].max(axis=1)
    traits_x['factoral_rarity'] = traits_x['factoral_rarity']/traits_x['factoral_rarity'].max()
    traits_x['rarity_rank'] = traits_x['rarity_rank']/traits_x['rarity_rank'].max()
    traits_x['trait_n'] = traits_x['trait_n']/traits_x['trait_n'].max()


    cols_2_keep = ['asset_id','collection','trait_n','mean_rarity','max_rarity','min_rarity',
                    'factoral_rarity','rarity_rank']


    traits = traits.append(traits_x[cols_2_keep])


sales = sales[sales.sale_price > 0.0001]
#convert price to dollars
sales['sale_minute'] =  sales["time"].dt.floor("min")
sales = sales.drop(columns="time")
latest_ETH_update = read_mongo(
    "eth-usd",
    return_df=True,
    query_sort=[("time", -1)],
    query_limit=1,
    query_projection=["time"],
)
if sales.sale_minute.max().to_pydatetime() > latest_ETH_update.time.iloc[0]:
    update_eth_usd()
ETH_USD = read_mongo(
    "eth-usd",
    return_df=True,
    query_filter={"time": {"$in": sales.sale_minute.to_list()}},
)
sales = sales.merge(ETH_USD, how="left", left_on="sale_minute", right_on="time")
sales["sale_USD"] = sales['sale_price']
ETH_sale = sales.sale_currency.isin(['WETH','ETH'])
#if sales are in ETH, convert USD price
sales.loc[ETH_sale,'sale_USD'] = sales.loc[ETH_sale,"sale_price"] * sales.loc[ETH_sale,"eth-usd-rate"]

#calculate rolling average price per collection
sales['collection_rolling_ave_USD'] = np.nan

sales = sales.sort_values(by=["collection","sale_minute"]).reset_index(drop=True)
for x in collections:
    df = sales[sales.collection==x]
    rolling_average_USD = (df["sale_USD"].rolling(window=100, center=True).median() )
    first50 = df.index[0:50]
    last50 = df.index[-49:]
    last200 = df.index[-199:]

    # first 50 sales are NA - so replace with expanding median
    rolling_average_USD.iloc[first50] = (
        df["sale_USD"].iloc[0:50].expanding().median()
    )

    # last 50 sales will also be NA, as we used centre = TRUE
    # so recalculate with centre = FALSE
    rolling_average_USD.iloc[last50] = (
        sales["sale-USD"].iloc[last200].rolling(100, center=False).median().iloc[last50]
    )

    sales['collection_rolling_ave_USD'].iloc[df.index] = rolling_average_USD

sales.head()
sales.shape



