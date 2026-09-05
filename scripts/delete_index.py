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
    timeout=60
)

index_name = "knowledge-assistant-index"

try:
    if client.indices.exists(index=index_name):
        response = client.indices.delete(index=index_name)
        print("Index deleted:", response)
    else:
        print("Index does not exist")
except Exception as e:
    print("Error:", e)
