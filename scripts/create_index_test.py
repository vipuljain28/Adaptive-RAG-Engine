import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts._aws_client import AWS_REGION, AWS_ACCOUNT_ID
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import botocore.session

c_id = "ssqzv0csspoou5ywa4pc"
host = f"https://{c_id}.{AWS_REGION}.aoss.amazonaws.com"
index_name = "knowledge-assistant-index"
url = f"{host}/{index_name}"

payload = {
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

session = botocore.session.Session()
credentials = session.get_credentials()
data = json.dumps(payload)

request = AWSRequest(method='PUT', url=url, data=data,
                     headers={'Content-Type': 'application/json'})
SigV4Auth(credentials, 'aoss', AWS_REGION).add_auth(request)

resp = requests.request(method='PUT', url=url, headers=dict(request.headers), data=data)
print(f"Status: {resp.status_code}")
print(resp.text)
