from azure.storage.blob import BlobClient, BlobServiceClient
import os
import blob.config as config
import pickle


def read_all(container_name):
    blob_service_client = BlobServiceClient.from_connection_string(
        config.connection_string
    )
    container_client = blob_service_client.get_container_client(container_name)
    blobs = container_client.list_blobs()
    return blobs


# download blobs - takes list of blobs and downloads them to the file_path
def download_blobs(blobs, file_path=config.file_path):
    # List blobs in container
    for blob in blobs.list_blobs():
        # skip blob name containing .DS_Store
        if ".DS_Store" in blob.name:
            continue
        blob_client = BlobClient.from_connection_string(
            conn_str=config.connection_string,
            container_name=config.container_name,
            blob_name=blob.name,
        )
        file_path = f"{file_path}/{blob.name}"
        # remove last everything after the last / from file_path
        file_path = file_path.rsplit("/", 1)[0]
        # create the directory if it doesn't exist
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        with open(f"./downloads/{blob.name}", "wb") as my_blob:
            print("Downloading blob to {}".format(file_path))
            blob_data = blob_client.download_blob()
            blob_data.readinto(my_blob)


# read downloaded .pkl file
def read_pkl(blob_path):
    file_path = f"{config.file_path}/{blob_path}"
    # check if file exists
    if not os.path.exists(file_path):
        all_blobs = read_all(config.container_name)
        # check to see if file exists in container
        for blob in all_blobs:
            if file_path in blob.name:
                download_blobs(file_path=blob_path)
                break

    try:
        with open(file_path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        print(e)
        return None
