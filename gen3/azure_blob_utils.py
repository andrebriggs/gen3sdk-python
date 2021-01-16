import sys
import time
import os
import pandas as pd
from datetime import datetime, timezone, timedelta
import logging
# See Az Blob samples here: https://github.com/Azure/azure-sdk-for-python/tree/master/sdk/storage/azure-storage-blob/samples
from azure.storage.blob import BlobServiceClient,ContainerClient, ResourceTypes, AccountSasPermissions, generate_blob_sas

# For Azure SDK logging see https://azuresdkdocs.blob.core.windows.net/$web/python/azure-storage-blob/12.6.0/index.html#logging
# Create a logger for the 'azure.storage.blob' SDK
logger = logging.getLogger('azure.storage.blob')
# logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configure a console output
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)

# You can find this in the Azure Portal on the storage account. 
CONNECTION_STRING = os.getenv('CONNECTION_STRING')
if CONNECTION_STRING is None:
    raise EnvironmentError("CONNECTION_STRING must be set as an ENV VAR")

def traverse_storage():
    print("Starting at " + time.strftime("%Y-%m-%d %H:%M"))
    
    # List containers in the storage account
    blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
    all_containers = blob_service_client.list_containers()

    rows = []
    for container in all_containers:
        print(f"\nContainer Name: '{container.name}''")
        container_client = ContainerClient.from_connection_string(CONNECTION_STRING, container_name=container.name)
        blobs = container_client.list_blobs()
        
        print("guid\tfilename\tsize\turls\tmd5")   # Print header
        for blob in blobs: 
            url = container_client.url+"/"+blob.name
            # sas_query = create_sas_query(container.name,blob.name,3600)
            # sas_url = container_client.primary_endpoint +"/"+blob.name+"?"+sas_query
            print("\t"+blob.name+"\t"+str(blob.size)+"\t"+url+"\t"+blob.content_settings.content_md5.hex())
            rows.append([None,blob.name,str(blob.size),url,blob.content_settings.content_md5.hex()])
            
        print()
    

    # df = pd.DataFrame.from_records(rows, columns=['guid', 'filename', 'size', 'urls', 'md5'])
    print("Done!")

def create_sas_query(container_name, blob_name, expires_in_seconds):
    blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)

    sas_query = generate_blob_sas(
        blob_service_client.account_name,
        container_name,
        blob_name,
        account_key=blob_service_client.credential.account_key,
        resource_types=ResourceTypes(object=True),
        permission=AccountSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(seconds=expires_in_seconds)
    )

    return sas_query

if __name__ == "__main__":
    traverse_storage()
    