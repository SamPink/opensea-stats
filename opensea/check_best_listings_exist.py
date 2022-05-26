import requests
import pandas as pd

import os, sys


currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)
from opensea.database import *
from opensea.opensea_events import *
from opensea.current_listings import *


def get_asset_listing(
    collection, token_id, limit=20, api_key="3eb775e344f14798b49718e86f55608c"
):
    asset_contract = read_mongo(
        f"{collection}_asset-all-info",
        query_limit=1,
        query_projection=["asset_contract_address"],
        return_df=True,
    )

    url = f"https://api.opensea.io/api/v1/asset/{asset_contract.asset_contract_address.iloc[0]}/{token_id}/listings"

    params = {
        "limit": limit,
    }

    headers = {"Accept": "application/json", "X-API-KEY": api_key}

    response = requests.request("GET", url, params=params, headers=headers)
    return response.json()


x = get_asset_listing("boredapeyachtclub", token_id=9419)



def confirm_listings(collection):
    current_listings = read_mongo(f"{collection}_still_listed",return_df=True, 
                        query_projection=['asset_id','listing_price'])
    
    actually_listed =[]

    for index,row in current_listings.iterrows():
        check_listed = get_asset_listing(collection=collection, token_id = int(row['asset_id']))
        if 'listings' not in check_listed.keys():
            time.sleep(2.5)
            check_listed = get_asset_listing(collection=collection, token_id = int(row['asset_id']))
        
        if len(check_listed['listings']) >=1:
            df = pd.DataFrame(check_listed['listings']).sort_values('created_date', ascending=False).reset_index()
            their_price = float(df.current_price.iloc[0])/1e18
            our_price = row['listing_price']
            perc_diff = abs((their_price-our_price)/our_price)
            if(perc_diff <3):
                actually_listed.append(row['asset_id'])
        
                
                
    curre
            
