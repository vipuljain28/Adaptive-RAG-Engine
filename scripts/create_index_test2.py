import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts._aws_client import AWS_REGION
import botocore.session
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

c_id = "ssqzv0csspoou5ywa4pc"
host = f"{c_id}.{AWS_REGION}.aoss.amazonaws.com"

session = botocore.session.Session()
credentials = session.get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, AWS_REGION, 'aoss', session_token=credentials.token)

client = OpenSearch(
    hosts=[{'host': host, 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=300
)

index_name = "knowledge-assistant-index"
index_body = {
    "settings": {
        "index": {
            "knn": True,
            "knn.algo_param.ef_search": 512
        }
    },
    "mappings": {
        "properties": {
            "embedding": {
                "type": "knn_vector",
                "dimension": 1024,
                "method": {
                    "name": "hnsw",
                    "engine": "nmslib",
                    "space_type": "l2"
                }
            },
            "text": {"type": "text"},
            "metadata": {"type": "text", "index": False}
        }
    }
}

try:
    if not client.indices.exists(index=index_name):
        response = client.indices.create(index=index_name, body=index_body)
        print("Index created:", response)
    else:
        print("Index already exists")
except Exception as e:
    print("Error:", e)
