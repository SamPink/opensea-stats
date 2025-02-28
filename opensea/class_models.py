import re
from pydantic import BaseModel
import datetime as dt


class sale_event(BaseModel):
    sale_id: int
    asset_id: int
    sale_quantity: int
    collection: str
    image_url: str
    time: dt.datetime
    event_type: str
    seller_wallet: str
    buyer_wallet: str
    block_hash: str
    sale_currency: str
    sale_price: float


# if None type, breaks the pydantic models
# so, convert none type to empty string
def None_to_str(string):
    if string is None:
        string = ""
    else:
        string = string
    return string


def MultiLevelNoneToStr(response_json, level_list=[]):
    x = response_json
    for i in range(len(level_list)):
        x = x[level_list[i]]
        if x is None:
            x = ""
            break
    return x


def get_asset_id(response_json):
    """function to pull out NFT ID"""
    name = response_json["asset"]["name"]

    # for ape gang old only
    # if name is not None andcontains " - TO MIGRATE"
    if name is not None and " - TO MIGRATE" in name:
        # remove " - TO MIGRATE"
        name = name.replace(" - TO MIGRATE", "")

    id = int(response_json["asset"]["token_id"])

    if id > 1e6 and name is None:
        asset_id = -69
    elif id > 1e6 and re.search("#\d+", name):
        asset_id = int(name.split("#")[1])
    elif id > 1e6:
        asset_id = name
    else:
        asset_id = id
    return asset_id


def dict_to_sales(response_json):
    """convert the JSON dictionary returned from opensea API to our defined sales event class"""
    # if item is a bundle (not single item)
    if response_json["asset"] is None:
        return None
    if response_json["asset"]["collection"]["slug"] != response_json["collection_slug"]:
        print("error in collection of returned asset")
        return None
    if response_json["quantity"] is None:
        response_json["quantity"] = 1

    if int(response_json["quantity"]) > 1:
        print("ignoring sale of bundle")
        return None

    if response_json["payment_token"] is None:
        print("Ignoring sale with no currency record")
        return None

    x = sale_event(
        **{
            "sale_id": int(response_json["id"]),
            "asset_id": get_asset_id(response_json),
            "sale_quantity": int(response_json["quantity"]),
            "collection": response_json["collection_slug"],
            "image_url": MultiLevelNoneToStr(response_json, ["asset", "image_url"]),
            "time": response_json["created_date"],
            "event_type": response_json["event_type"],
            "seller_wallet": MultiLevelNoneToStr(response_json, ["seller", "address"]),
            "buyer_wallet": MultiLevelNoneToStr(
                response_json, ["winner_account", "address"]
            ),
            "block_hash": MultiLevelNoneToStr(
                response_json, ["transaction", "block_hash"]
            ),
            # info about sale price
            "sale_currency": MultiLevelNoneToStr(
                response_json, ["payment_token", "symbol"]
            ),
            "sale_price": int(response_json["total_price"]) / 1e18,
        }
    )
    return x


class transfer_event(BaseModel):
    transfer_id: int
    asset_id: int
    sale_quantity: int
    collection: str
    image_url: str
    time: dt.datetime
    event_type: str
    from_wallet: str
    to_wallet: str
    block_hash: str


def dict_to_transfer(response_json):
    # if item is a bundle (not single item)
    if response_json["asset"] is None:
        return None
    if response_json["asset"]["collection"]["slug"] != response_json["collection_slug"]:
        print("error in collection of returned asset")
        return None
    if response_json["quantity"] is None:
        response_json["quantity"] = 1
    if int(response_json["quantity"]) > 1:
        print("ignoring transfer of bundle")
        return None

    x = transfer_event(
        **{
            "transfer_id": int(response_json["id"]),
            "asset_id": get_asset_id(response_json),
            "sale_quantity": int(response_json["quantity"]),
            "collection": response_json["collection_slug"],
            "image_url": MultiLevelNoneToStr(response_json, ["asset", "image_url"]),
            "time": response_json["created_date"],
            "event_type": response_json["event_type"],
            "from_wallet": MultiLevelNoneToStr(
                response_json, ["transaction", "from_account", "address"]
            ),
            "to_wallet": MultiLevelNoneToStr(
                response_json, ["transaction", "to_account", "address"]
            ),
            "block_hash": MultiLevelNoneToStr(
                response_json, ["transaction", "block_hash"]
            ),
        }
    )
    return x


class listing_event(BaseModel):
    listing_id: int
    asset_id: int
    collection: str
    event_type: str
    time: dt.datetime
    seller_address: str
    listing_currency: str
    auction_type: str
    private_auction: bool
    listing_price: float
    duration: int


def dict_to_listing(response_json):
    """convert the JSON dictionary returned from opensea API to our defined listing event class"""
    if response_json["asset"] is None:
        return None
    if response_json["asset"]["collection"]["slug"] != response_json["collection_slug"]:
        print("error in collection of returned asset")
        return None
    if int(response_json["quantity"]) > 1:
        print("ignoring listing of bundle")
        return None

    if response_json["is_private"] is None:
        response_json["is_private"] = False

    if response_json["ending_price"] is None:
        print(f"listing of #{get_asset_id(response_json)} with no price")
        return None

    if response_json["payment_token"] is None:
        print("Ignoring listings with no currency record")
        return None

    if response_json["duration"] is None:
        auction_time = 1e9
    else:
        auction_time = response_json["duration"]

    x = listing_event(
        **{
            "listing_id": int(response_json["id"]),
            "asset_id": get_asset_id(response_json),
            "collection": None_to_str(response_json["collection_slug"]),
            "event_type": response_json["event_type"],
            "private_auction": response_json["is_private"],
            "auction_type": None_to_str(response_json["auction_type"]),
            "time": response_json["created_date"],
            "seller_address": MultiLevelNoneToStr(response_json, ["seller", "address"]),
            "duration": auction_time,
            "listing_currency": MultiLevelNoneToStr(
                response_json, ["payment_token", "symbol"]
            ),
            "listing_price": int(response_json["ending_price"]) / 1e18,
        }
    )
    return x


class cancellation_event(BaseModel):
    listing_id: int
    asset_id: int
    collection: str
    event_type: str
    time: dt.datetime
    seller_address: str


def dict_to_canc(response_json):
    """convert the JSON dictionary returned from opensea API to our defined cancellation event class"""
    if response_json["asset"] is None:
        return None
    if response_json["asset"]["collection"]["slug"] != response_json["collection_slug"]:
        print("error in collection of returned asset")
        return None
    if response_json["quantity"] is None:
        response_json["quantity"] = 1

    if int(response_json["quantity"]) > 1:
        print("ignoring cancellation of bundle")
        return None

    x = cancellation_event(
        **{
            "listing_id": int(response_json["id"]),
            "asset_id": get_asset_id(response_json),
            "collection": response_json["collection_slug"],
            "event_type": response_json["event_type"],
            "time": response_json["created_date"],
            "seller_address": MultiLevelNoneToStr(response_json, ["seller", "address"]),
        }
    )

    return x
