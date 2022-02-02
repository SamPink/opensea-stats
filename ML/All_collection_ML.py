# # Load Libraries
import pandas as pd
import numpy as np
import datetime as dt
import numpy as np
import matplotlib.pyplot as plt
import datetime as dt
import re
import time

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
from opensea.opensea_assets import get_collection_assets
from opensea.opensea_events import update_opensea_events




database = connect_mongo()
db_collections = database.collection_names(include_system_collections=False)
sales_regex = re.compile('.*_sales')
sales_collections = list(filter(sales_regex.match, db_collections))
collection_with_sales = [re.sub('_sales','',i) for i in sales_collections]



traits_regex = re.compile('.*_traits')
traits_collections = list(filter(traits_regex.match, db_collections))
collection_with_traits = [re.sub('_traits','',i) for i in traits_collections]


"""missing_traits = list(set(collection_with_sales) - set(collection_with_traits))
for i in missing_traits:
    get_collection_assets(i)
    time.sleep(60)
    update_opensea_events(i,eventTypes=["sales"])
    time.sleep(60)
    update_opensea_events(i,eventTypes=["sales"],
                          find_firstUpdated_from_DB=True, find_lastUpdated_from_DB=False)"""


database = connect_mongo()
db_collections2 = database.collection_names(include_system_collections=False)
traits_collections2 = list(filter(traits_regex.match, db_collections2))
collection_with_traits2 = [re.sub('_traits','',i) for i in traits_collections2]

collections = list(set.intersection(set(collection_with_sales),set(collection_with_traits2)))


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


    cols_2_keep = ['asset_id','collection','trait_n','trait_n_rarity',
                    'mean_rarity','max_rarity','min_rarity',
                    'factoral_rarity','rarity_rank']


    traits = traits.append(traits_x[cols_2_keep])


sales = sales[sales.sale_price > 0.0001]
#convert price to dollars
sales['sale_minute'] =  sales["time"].dt.floor("h")
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
print(sales[(sales.collection == 'boredapeyachtclub') & (sales.asset_id == 9485)& (sales.sale_price==45)])

sales = sales.merge(ETH_USD, how="left", left_on="sale_minute", right_on="time")
sales["sale_USD"] = sales['sale_price']
ETH_sale = sales.sale_currency.isin(['WETH','ETH'])
#if sales are in ETH, convert USD price
sales.loc[ETH_sale,'sale_USD'] = sales.loc[ETH_sale,"sale_price"] * sales.loc[ETH_sale,"eth-usd-rate"]

#make all apegang 
AG_new = sales.collection =='ape-gang'
sales.loc[AG_new,'collection'] = 'ape-gang-old'

#calculate rolling average price per collection
sales['collection_rolling_ave_USD'] = np.nan

sales = sales.sort_values(by=["collection","sale_minute"]).reset_index(drop=True)
for x in sales.collection.unique():
    df = sales[sales.collection==x]
    rolling_average_USD = (df["sale_USD"].rolling(window=100, center=True).median() )


    # first 50 sales are NA - so replace with expanding median
    rolling_average_USD.iloc[0:50] = (
        df["sale_USD"].iloc[0:50].expanding().median()
    )

    # last 50 sales will also be NA, as we used centre = TRUE
    # so recalculate with centre = FALSE
    rolling_average_USD.iloc[-49:] = (
        df["sale_USD"].iloc[-151:].rolling(100, center=False).median().iloc[-49:]
    )

    sales['collection_rolling_ave_USD'].iloc[df.index] = rolling_average_USD
    thingy = rolling_average_USD.isna().sum()
    print(f"collection = {x}, and has {thingy} NAs")

traits['asset_id'] = pd.to_numeric(traits['asset_id'])
df = sales.merge(traits, on=['collection','asset_id'],how='inner')
df.shape[0]

from scipy.stats import pearsonr
price_perc = df.sale_USD/df.collection_rolling_ave_USD
df = df[price_perc >0.2]
price_perc = price_perc[price_perc >0.2]




x = df[['collection_rolling_ave_USD', 'trait_n_rarity', 'mean_rarity', 'max_rarity', 'min_rarity',
                'factoral_rarity', 'rarity_rank']]

y= df['sale_USD']

X_train, X_test, y_train, y_test = train_test_split(
    x, y, test_size=0.15, random_state=42
)

rf_reg = RandomForestRegressor()

rf_reg.fit(X_train, y_train)
y_pred = rf_reg.predict(X_test)

mae = mean_absolute_error(y_test, y_pred)

import plotly.express as px
p =  px.scatter(x=y_test, y = y_pred,opacity =0.2,  trendline="lowess")
p.show()

import joblib
joblib.dump(rf_reg, 'All_Collection_ML.joblib')
