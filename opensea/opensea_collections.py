from database import connect_mongo
import re


def all_collection_names():
    database = connect_mongo()
    db_collections = database.collection_names(include_system_collections=False)
    sales_regex = re.compile(".*_sales")
    sales_collections = list(filter(sales_regex.match, db_collections))
    collection_with_sales = [re.sub("_sales", "", i) for i in sales_collections]

    return collection_with_sales


def all_collections_with_traits():
    database = connect_mongo()
    db_collections = database.collection_names(include_system_collections=False)
    traits_regex = re.compile(".*_traits")
    traits_collections = list(filter(traits_regex.match, db_collections))
    collection_with_traits = [re.sub("_traits", "", i) for i in traits_collections]

    return collection_with_traits
