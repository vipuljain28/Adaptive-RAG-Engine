"""
scripts/setup_opensearch.py — Create OpenSearch Serverless collection for the KB.

Creates:
  - Encryption security policy
  - Network security policy  (public access so Bedrock KB can reach it)
  - Data access policy       (grants KB IAM role full index access)
  - Vector search collection

Writes OPENSEARCH_COLLECTION_ARN back to .env automatically.

Usage:
    python scripts/setup_opensearch.py
"""

import json, os, re, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

from scripts._aws_client import get_client, AWS_REGION, AWS_ACCOUNT_ID

COLLECTION_NAME = "knowledge-assistant"
KB_ROLE_NAME    = "knowledge-assistant-kb-role"


def write_env(key: str, value: str):
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if not os.path.exists(env_path):
        print(f"  .env not found — set manually: {key}={value}"); return
    with open(env_path, "r") as f:
        content = f.read()
    pattern = rf"^{re.escape(key)}=.*$"
    replacement = f"{key}={value}"
    if re.search(pattern, content, flags=re.MULTILINE):
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    else:
        content += f"\n{replacement}\n"
    with open(env_path, "w") as f:
        f.write(content)
    print(f"  Written to .env: {key}={value}")


def ensure_kb_role(iam) -> str:
    """Create (or fetch) the IAM role that the KB will use."""
    print(f"\nStep 1: IAM Role — {KB_ROLE_NAME}")
    try:
        role = iam.get_role(RoleName=KB_ROLE_NAME)
        arn  = role["Role"]["Arn"]
        print(f"  Already exists: {arn}")
    except iam.exceptions.NoSuchEntityException:
        trust = json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "bedrock.amazonaws.com"},
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {"aws:SourceAccount": AWS_ACCOUNT_ID}
                }
            }]
        })
        role = iam.create_role(
            RoleName=KB_ROLE_NAME,
            AssumeRolePolicyDocument=trust,
            Description="IAM role for Bedrock Knowledge Base",
        )
        arn = role["Role"]["Arn"]
        print(f"  Created: {arn}")

        for policy in [
            "arn:aws:iam::aws:policy/AmazonBedrockFullAccess",
            "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess",
        ]:
            iam.attach_role_policy(RoleName=KB_ROLE_NAME, PolicyArn=policy)
            print(f"  Attached: {policy.split('/')[-1]}")

    aoss_policy = json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": "aoss:APIAccessAll",
            "Resource": f"arn:aws:aoss:{AWS_REGION}:{AWS_ACCOUNT_ID}:collection/*"
        }]
    })
    iam.put_role_policy(
        RoleName=KB_ROLE_NAME,
        PolicyName="OpenSearchServerlessAccess",
        PolicyDocument=aoss_policy,
    )
    print("  Ensured OpenSearchServerlessAccess policy on KB role.")

    print("  Waiting 15s for IAM propagation...")
    time.sleep(15)
    return arn


def create_collection(aoss, kb_role_arn: str) -> tuple[str, str]:
    """Create OpenSearch Serverless collection. Returns (collection_id, collection_arn)."""
    print(f"\nStep 2: OpenSearch Serverless — {COLLECTION_NAME}")

    # ── Check if collection already exists ─────────────────────────────────────
    try:
        resp = aoss.batch_get_collection(names=[COLLECTION_NAME])
        existing = resp.get("collectionDetails", [])
        if existing:
            c_id  = existing[0]["id"]
            c_arn = existing[0]["arn"]
            print(f"  Collection already exists: {c_id}")
            return c_id, c_arn
    except Exception:
        pass

    enc_policy_name = f"{COLLECTION_NAME}-enc"
    net_policy_name = f"{COLLECTION_NAME}-net"
    acc_policy_name = f"{COLLECTION_NAME}-access"

    # ── Encryption policy ───────────────────────────────────────────────────────
    print("  Creating encryption policy...")
    try:
        aoss.create_security_policy(
            name=enc_policy_name,
            type="encryption",
            policy=json.dumps({
                "Rules": [{
                    "Resource":     [f"collection/{COLLECTION_NAME}"],
                    "ResourceType": "collection"
                }],
                "AWSOwnedKey": True
            }),
        )
        print("  Encryption policy created.")
    except aoss.exceptions.ConflictException:
        print("  Encryption policy already exists.")

    # ── Network policy (public) ─────────────────────────────────────────────────
    print("  Creating network policy...")
    try:
        aoss.create_security_policy(
            name=net_policy_name,
            type="network",
            policy=json.dumps([{
                "Rules": [
                    {"Resource": [f"collection/{COLLECTION_NAME}"], "ResourceType": "collection"},
                    {"Resource": [f"collection/{COLLECTION_NAME}"], "ResourceType": "dashboard"},
                ],
                "AllowFromPublic": True
            }]),
        )
        print("  Network policy created.")
    except aoss.exceptions.ConflictException:
        print("  Network policy already exists.")

    # ── Data access policy ──────────────────────────────────────────────────────
    print("  Creating data access policy...")
    sts = get_client("sts")
    caller_arn = sts.get_caller_identity()["Arn"]
    principals = list(set([kb_role_arn, caller_arn]))

    data_policy = [{
        "Rules": [
            {
                "Resource":     [f"collection/{COLLECTION_NAME}"],
                "Permission":   [
                    "aoss:CreateCollectionItems",
                    "aoss:DeleteCollectionItems",
                    "aoss:UpdateCollectionItems",
                    "aoss:DescribeCollectionItems",
                ],
                "ResourceType": "collection",
            },
            {
                "Resource":     [f"index/{COLLECTION_NAME}/*"],
                "Permission":   [
                    "aoss:CreateIndex",
                    "aoss:DeleteIndex",
                    "aoss:UpdateIndex",
                    "aoss:DescribeIndex",
                    "aoss:ReadDocument",
                    "aoss:WriteDocument",
                ],
                "ResourceType": "index",
            }
        ],
        "Principal": principals,
    }]

    try:
        aoss.create_access_policy(
            name=acc_policy_name,
            type="data",
            policy=json.dumps(data_policy),
        )
        print("  Data access policy created.")
    except aoss.exceptions.ConflictException:
        try:
            p_detail = aoss.get_access_policy(name=acc_policy_name, type="data")["accessPolicyDetail"]
            aoss.update_access_policy(
                name=acc_policy_name,
                type="data",
                policyVersion=p_detail["policyVersion"],
                policy=json.dumps(data_policy),
            )
            print("  Data access policy updated with caller & role permissions.")
        except Exception as ex:
            print(f"  Data access policy already exists ({ex}).")

    # ── Create collection ───────────────────────────────────────────────────────
    print("  Creating collection (this takes 2–4 minutes)...")
    resp   = aoss.create_collection(name=COLLECTION_NAME, type="VECTORSEARCH")
    c_id   = resp["createCollectionDetail"]["id"]
    c_arn  = resp["createCollectionDetail"]["arn"]
    print(f"  Collection ID  : {c_id}")
    print(f"  Collection ARN : {c_arn}")

    # ── Wait for ACTIVE status ──────────────────────────────────────────────────
    print("  Waiting for collection to become ACTIVE", end="", flush=True)
    for _ in range(40):
        time.sleep(15)
        detail = aoss.batch_get_collection(ids=[c_id])["collectionDetails"]
        status = detail[0]["status"] if detail else "CREATING"
        print(".", end="", flush=True)
        if status == "ACTIVE":
            print(" ACTIVE")
            break
        if status == "FAILED":
            print(" FAILED"); sys.exit(1)
    else:
        print("\nTimeout waiting for collection — check AWS console.")

    return c_id, c_arn


def create_vector_index(c_id: str):
    print("\nStep 3: Creating Vector Index on Data Plane")
    host = f"{c_id}.{AWS_REGION}.aoss.amazonaws.com"
    index_name = "knowledge-assistant-index"
    
    try:
        from opensearchpy import OpenSearch, RequestsHttpConnection
        from requests_aws4auth import AWS4Auth
        import botocore.session
    except ImportError:
        print("  Missing opensearch-py or requests-aws4auth. Skipping index creation.")
        return

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
                print(f"  Index created successfully: {index_name}")
                print("  Waiting 60s for index propagation across AWS...")
                time.sleep(60)
            else:
                print(f"  Index {index_name} already exists.")
            return
        except Exception as e:
            err = str(e)
            if "Forbidden" in err or "403" in err:
                print(f"  Attempt {attempt+1}: Access Denied (waiting for IAM propagation)...")
            else:
                print(f"  Attempt {attempt+1} Error: {err}")
        time.sleep(15)
    print("  WARNING: Could not create index. KB setup might fail.")


def main():
    print("=" * 60)
    print("OpenSearch Serverless Setup")
    print("=" * 60)

    iam  = get_client("iam")
    aoss = get_client("opensearchserverless")

    # Step 1: IAM role
    kb_role_arn = ensure_kb_role(iam)

    # Step 2: Collection
    c_id, c_arn = create_collection(aoss, kb_role_arn)

    # Step 3: Create Vector Index
    create_vector_index(c_id)

    # Write back to .env
    print("\nWriting to .env ...")
    write_env("OPENSEARCH_COLLECTION_ARN", c_arn)

    print("\n" + "=" * 60)
    print("OpenSearch setup complete!")
    print(f"  Collection ARN : {c_arn}")
    print("\nNext: python scripts/setup_knowledge_base.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
