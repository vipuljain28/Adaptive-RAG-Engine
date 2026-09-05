import sys, os, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from dotenv import load_dotenv
load_dotenv()
import boto3
aoss = boto3.client('opensearchserverless', region_name='us-east-1', verify=False)
r = aoss.list_collections()
collections = r.get('collectionSummaries', [])
print(f"Found {len(collections)} collection(s):")
for c in collections:
    print(f"  name={c.get('name')} id={c.get('id')} status={c.get('status')} arn={c.get('arn')}")
    # Get endpoint
    try:
        detail = aoss.batch_get_collection(ids=[c['id']])
        for d in detail.get('collectionDetails', []):
            print(f"  endpoint={d.get('collectionEndpoint')}")
    except Exception as e:
        print(f"  endpoint error: {e}")
