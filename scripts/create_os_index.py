import os
import sys
import time

def create_vector_index(collection_id: str, aws_region: str):
    print(f"Creating Vector Index on Data Plane for collection {collection_id} in {aws_region}")
    host = f"{collection_id}.{aws_region}.aoss.amazonaws.com"
    index_name = "knowledge-assistant-index"
    
    try:
        from opensearchpy import OpenSearch, RequestsHttpConnection
        from requests_aws4auth import AWS4Auth
        import botocore.session
    except ImportError:
        print("Missing opensearch-py or requests-aws4auth. Skipping index creation.")
        return

    session = botocore.session.Session()
    credentials = session.get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, aws_region, 'aoss', session_token=credentials.token)

    client = OpenSearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=60
    )

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
                        "engine": "faiss",
                        "space_type": "l2"
                    }
                },
                "text": {"type": "text"},
                "metadata": {"type": "text", "index": False}
            }
        }
    }

    for attempt in range(10):
        try:
            if not client.indices.exists(index=index_name):
                client.indices.create(index=index_name, body=index_body)
                print(f"Index created successfully: {index_name}")
                print("Waiting 60s for index propagation across AWS...")
                time.sleep(60)
            else:
                print(f"Index {index_name} already exists.")
            return
        except Exception as e:
            err = str(e)
            if "Forbidden" in err or "403" in err:
                print(f"Attempt {attempt+1}: Access Denied (waiting for IAM propagation)...")
            else:
                print(f"Attempt {attempt+1} Error: {err}")
        time.sleep(15)
    print("WARNING: Could not create index.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_os_index.py <collection_id> <aws_region>")
        sys.exit(1)
    create_vector_index(sys.argv[1], sys.argv[2])
