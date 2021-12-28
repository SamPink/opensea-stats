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
    sale_price: int


def dict_to_sales(response_json):
    """convert the JSON dictionary returned from opensea API to our defined sales event class"""
    # if item is a bundle (not single item)
    if int(response_json["quantity"]) > 1:
        print("ignoring sale of bundle")
        return None

    x = sale_event(
        **{
            "sale_id": int(response_json["id"]),
            "asset_id": int(response_json["asset"]["token_id"]),
            "sale_quantity": int(response_json["quantity"]),
            "collection": response_json["collection_slug"],
            "image_url": response_json["asset"]["image_url"],
            "time": response_json["created_date"],
            "event_type": response_json["event_type"],
            "seller_wallet": response_json["seller"]["address"],
            "buyer_wallet": response_json["winner_account"]["address"],
            "block_hash": response_json["transaction"]["block_hash"],
            # info about sale price
            "sale_currency": response_json["payment_token"]["symbol"],
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
    if int(response_json["quantity"]) > 1:
        print("ignoring transfer of bundle")
        return None

    x = transfer_event(
        **{
            "transfer_id": int(response_json["id"]),
            "asset_id": int(response_json["asset"]["token_id"]),
            "sale_quantity": int(response_json["quantity"]),
            "collection": response_json["collection_slug"],
            "image_url": response_json["asset"]["image_url"],
            "time": response_json["created_date"],
            "event_type": response_json["event_type"],
            "from_wallet": response_json["transaction"]["from_account"]["address"],
            "to_wallet": response_json["transaction"]["to_account"]["address"],
            "block_hash": response_json["transaction"]["block_hash"],
        }
    )


class listing_event(BaseModel):
    listing_id: int
    asset_id: int
    collection: str
    event_type: str
    time: dt.datetime
    seller_address: str
    listing_price: int


def dict_to_listing(response_json):
    """convert the JSON dictionary returned from opensea API to our defined listing event class"""
    if int(response_json["quantity"]) > 1:
        print("ignoring listing of bundle")
        return None

    x = listing_event(
        **{
            "listing_id": int(response_json["id"]),
            "asset_id": int(response_json["asset"]["token_id"]),
            "collection": response_json["collection_slug"],
            "event_type": response_json["event_type"],
            "time": response_json["created_date"],
            "seller_address": response_json["seller"]["address"],
            "listing_price": int(response_json["ending_price"]) / 1e18,
        }
    )
    return x


class eventCancelled(BaseModel):
    test: str
