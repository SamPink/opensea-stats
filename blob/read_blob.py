from azure.storage.blob import BlobClient, BlobServiceClient
import os
import config as config


def read_all(container_name=config.container_name, opensea_collection=None):
    blob_service_client = BlobServiceClient.from_connection_string(
        config.connection_string
    )
    container_client = blob_service_client.get_container_client(container_name)
    blobs = container_client.list_blobs()
    all_blobs = []
    for blob in blobs:
        if opensea_collection is not None:
            # if collection contains in blob name
            if opensea_collection in blob.name:
                all_blobs.append(blob["name"])
        else:
            all_blobs.append(blob["name"])
    return all_blobs


# download blobs - takes list of blobs and downloads them to the file_path
def download_blobs(blobs, path=config.file_path):
    # List blobs in container
    for blob in blobs:
        # skip blob name containing .DS_Store
        if ".DS_Store" in blob:
            continue
        blob_client = BlobClient.from_connection_string(
            conn_str=config.connection_string,
            container_name=config.container_name,
            blob_name=blob,
        )
        file_path = f"{path}/{blob}"
        # remove last everything after the last / from file_path
        file_path = file_path.rsplit("/", 1)[0]
        # create the directory if it doesn't exist
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        with open(f"{path}/{blob}", "wb") as my_blob:
            print("Downloading blob to {}".format(file_path))
            blob_data = blob_client.download_blob()
            blob_data.readinto(my_blob)


# read downloaded .pkl file
def read_pkl(collection_name):
    all_blobs = read_all(opensea_collection=collection_name)

    # find file containing _price_pred_model.pkl
    for blob in all_blobs:
        if "_price_pred_model.pkl" in blob:
            model_path = f"{config.file_path}/{blob}"
        if "_scaler.pkl" in blob:
            scaler_path = f"{config.file_path}/{blob}"

    # check if file exists
    if not os.path.exists(model_path):
        download_blobs(all_blobs)

    return model_path, scaler_path

    """ 
    #dont load to memory as it requires a ML libs
    try:
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        with open(scaler_path, "rb") as f:
            scaler = pickle.load(f)

        return model, scaler
    except Exception as e:
        print(e)
        return None """


# blobs = read_all(opensea_collection="world-of-women-nft")

# model, scaler = read_pkl("cool-cats-nft")
