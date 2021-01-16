import sys
import logging
import random
import rstr
import json
import time

from gen3.auth import Gen3Auth
from gen3.tools.indexing import index_object_manifest
from gen3.submission import Gen3Submission
from gen3.file import Gen3File

logging.basicConfig(filename="output.log", level=logging.DEBUG)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

tried_words = False
WORDS = None

COMMONS_URL = "http://localhost/"
AWS_MANIFEST = "./aws_manifest.tsv"
AZURE_MANIFEST = "./azure_manifest.tsv"
PROGRAM_NAME = "Program1"

def simple_generate_string_data(size=10):
    return rstr.xeger("^[0-9a-f]{" + str(size) + "}")

def generate_number(minx=0, maxx=100, is_int=False):
    return random.randint(minx, maxx) if is_int else random.uniform(minx, maxx)

def index_azure_blobs():
    # use basic auth for admin privileges in indexd
    auth = ("indexd_client", "indexd_client_pass")

    index_object_manifest(
        commons_url=COMMONS_URL,
        manifest_file=AZURE_MANIFEST,
        thread_num=8,
        auth=auth,
        replace_urls=False,
        manifest_file_delimiter="\t", # put "," if the manifest is csv file
        output_filename="azure-output-manifest.tsv"
    )

def index_s3_objects():
    # use basic auth for admin privileges in indexd
    auth = ("indexd_client", "indexd_client_pass")

    index_object_manifest(
        commons_url=COMMONS_URL,
        manifest_file=AWS_MANIFEST,
        thread_num=8,
        auth=auth,
        replace_urls=False,
        manifest_file_delimiter="\t" # put "," if the manifest is csv file
    )

def create_slide_image_json(index_guid, file_name, md5_value, file_size):
    return {
            "data_category": "Slide Image", #
            "md5sum": md5_value, 
            "core_metadata_collections": {
                "node_id": "b7710d99-98f1-4cd4-8006-b500dfc02729", # Hardcoded!!!
                "submitter_id": "core_metadata_collection_2c856e2a92"  # Hardcoded!!!
            }, 
            "submitter_id": "slide_image_"+simple_generate_string_data(10), 
            "type": "slide_image", #
            "file_name": file_name, 
            "object_id": index_guid, 
            "data_format": simple_generate_string_data(10), 
            "file_size": file_size, 
            "experimental_strategy": "Diagnostic Slide", #
            "data_type": "image", 
        }

def submit_nodes_to_graph(gen3_node_json):
    auth = Gen3Auth(endpoint="http://localhost",refresh_file="credentials-2.json")
    sheepdog_client = Gen3Submission("http://localhost", auth)
    # slide_image_json = create_slide_image_json("820a6f0f-34fd-4e23-8780-c11c378288d9","F9sfEjj.gif","8d9b77ae91db4e72ca9053bde9a010c7",1013143) # AWS
    # slide_image_json = create_slide_image_json("bc12dcc2-cd6a-43a1-83a3-ae5a9ab66ef1","giphy-6.gif","153b0bb27b6689f45fb7493abe1faa3b",1596362) # AWS

    

    logging.info(f"Created json file:\n{json.dumps(gen3_node_json, indent=2)}\n")
    json_result = sheepdog_client.submit_record(PROGRAM_NAME,"P1",gen3_node_json)
    logging.info(f"\n\njson result:\n\n{json_result}")
        
def get_presigned_url(node_guid,file_protocol):
    auth = Gen3Auth(endpoint="http://localhost",refresh_file="credentials-2.json")
    fence_client = Gen3File(endpoint="http://localhost",auth_provider=auth)
    json_result = fence_client.get_presigned_url(node_guid,protocol=file_protocol)
    logging.info(f"\n\njson result:\n\n{json_result}\n")
    logging.info(f"\n\nPlease visit this address in your browser:\n\nhttps://localhost/files/{node_guid}\n")



def main():
    print("Starting at " + time.strftime("%Y-%m-%d %H:%M")+"\n")
    # index_s3_objects()
    # index_azure_blobs()

    # azure_gen3_data_node = create_slide_image_json("90b7a6cf-59f5-4607-ad25-e6864627667f","giphy-6.gif","153b0bb27b6689f45fb7493abe1faa3b",1596362) # Azure
    # submit_nodes_to_graph(azure_gen3_data_node)
    
    azure_node_guid = "90b7a6cf-59f5-4607-ad25-e6864627667f"
    get_presigned_url(azure_node_guid, "https")


if __name__ == "__main__":
    main()