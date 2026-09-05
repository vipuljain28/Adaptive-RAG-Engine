"""
scripts/setup_knowledge_base.py — Create Bedrock Knowledge Base + start ingestion.

Prerequisites:
  1. setup_s3.py         — S3 bucket exists
  2. upload_documents.py — documents uploaded to S3
  3. setup_opensearch.py — OPENSEARCH_COLLECTION_ARN set in .env

Usage:
    python scripts/setup_knowledge_base.py
"""

import os, re, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

from scripts._aws_client import get_client, AWS_REGION, AWS_ACCOUNT_ID

S3_BUCKET_NAME            = os.getenv("S3_BUCKET_NAME",            "")
EMBEDDING_MODEL_ID        = os.getenv("EMBEDDING_MODEL_ID",        "amazon.titan-embed-text-v2:0")
OPENSEARCH_COLLECTION_ARN = os.getenv("OPENSEARCH_COLLECTION_ARN", "")
KB_ROLE_NAME              = "knowledge-assistant-kb-role"
KB_NAME                   = "knowledge-assistant-kb"
DS_NAME                   = "s3-company-documents"
VECTOR_INDEX_NAME         = "knowledge-assistant-index"


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


def get_role_arn(iam) -> str:
    try:
        return iam.get_role(RoleName=KB_ROLE_NAME)["Role"]["Arn"]
    except Exception:
        print(f"ERROR: IAM role {KB_ROLE_NAME} not found.")
        print("       Run: python scripts/setup_opensearch.py first")
        sys.exit(1)


def create_knowledge_base(bedrock_agent, role_arn: str) -> tuple[str, str]:
    print(f"\nStep 1: Creating Knowledge Base — {KB_NAME}")

    try:
        kbs = bedrock_agent.list_knowledge_bases(maxResults=100).get("knowledgeBaseSummaries", [])
        for kb in kbs:
            if kb["name"] == KB_NAME:
                print(f"  KB already exists: {kb['knowledgeBaseId']}")
                # We need the full ARN, which might require getting the KB detail
                kb_detail = bedrock_agent.get_knowledge_base(knowledgeBaseId=kb['knowledgeBaseId'])['knowledgeBase']
                return kb_detail['knowledgeBaseId'], kb_detail['knowledgeBaseArn']
    except Exception as e:
        print(f"  Warning: error checking existing KBs: {e}")

    embedding_arn = (
        f"arn:aws:bedrock:{AWS_REGION}::foundation-model/{EMBEDDING_MODEL_ID}"
    )

    resp = bedrock_agent.create_knowledge_base(
        name=KB_NAME,
        description="Knowledge base for company internal documents",
        roleArn=role_arn,
        knowledgeBaseConfiguration={
            "type": "VECTOR",
            "vectorKnowledgeBaseConfiguration": {
                "embeddingModelArn": embedding_arn,
            },
        },
        storageConfiguration={
            "type": "OPENSEARCH_SERVERLESS",
            "opensearchServerlessConfiguration": {
                "collectionArn":   OPENSEARCH_COLLECTION_ARN,
                "vectorIndexName": VECTOR_INDEX_NAME,
                "fieldMapping": {
                    "vectorField":   "embedding",
                    "textField":     "text",
                    "metadataField": "metadata",
                },
            },
        },
    )

    kb     = resp["knowledgeBase"]
    kb_id  = kb["knowledgeBaseId"]
    kb_arn = kb["knowledgeBaseArn"]
    print(f"  KB ID  : {kb_id}")
    print(f"  KB ARN : {kb_arn}")

    # Wait until ACTIVE
    print("  Waiting for KB to become ACTIVE", end="", flush=True)
    for _ in range(20):
        time.sleep(10)
        kb_status = bedrock_agent.get_knowledge_base(knowledgeBaseId=kb_id)
        status    = kb_status["knowledgeBase"]["status"]
        print(".", end="", flush=True)
        if status == "ACTIVE":
            print(" ACTIVE")
            break
        if status == "FAILED":
            print(f" FAILED: {kb_status}")
            sys.exit(1)

    return kb_id, kb_arn


def create_data_source(bedrock_agent, kb_id: str) -> str:
    print(f"\nStep 2: Creating Data Source — {DS_NAME}")

    try:
        dss = bedrock_agent.list_data_sources(knowledgeBaseId=kb_id, maxResults=100).get("dataSourceSummaries", [])
        for ds in dss:
            if ds["name"] == DS_NAME:
                print(f"  Data Source already exists: {ds['dataSourceId']}")
                return ds['dataSourceId']
    except Exception as e:
        print(f"  Warning: error checking existing DS: {e}")

    bucket_arn = f"arn:aws:s3:::{S3_BUCKET_NAME}"
    resp = bedrock_agent.create_data_source(
        knowledgeBaseId=kb_id,
        name=DS_NAME,
        description="Company documents stored in S3",
        dataSourceConfiguration={
            "type": "S3",
            "s3Configuration": {
                "bucketArn":         bucket_arn,
                "inclusionPrefixes": ["documents/"],
            },
        },
        vectorIngestionConfiguration={
            "chunkingConfiguration": {
                "chunkingStrategy": "FIXED_SIZE",
                "fixedSizeChunkingConfiguration": {
                    "maxTokens":         512,
                    "overlapPercentage": 20,
                },
            }
        },
    )
    ds_id = resp["dataSource"]["dataSourceId"]
    print(f"  Data Source ID: {ds_id}")
    return ds_id


def start_ingestion(bedrock_agent, kb_id: str, ds_id: str) -> str:
    print(f"\nStep 3: Starting ingestion job...")
    resp   = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=kb_id,
        dataSourceId=ds_id,
    )
    job_id = resp["ingestionJob"]["ingestionJobId"]
    print(f"  Job ID: {job_id}")

    # Poll until complete
    print("  Waiting for ingestion to complete", end="", flush=True)
    for _ in range(40):
        time.sleep(15)
        job = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=ds_id,
            ingestionJobId=job_id,
        )["ingestionJob"]
        status = job["status"]
        print(".", end="", flush=True)
        if status == "COMPLETE":
            stats = job.get("statistics", {})
            print(f" COMPLETE")
            print(f"  Documents scanned  : {stats.get('numberOfDocumentsScanned', '?')}")
            print(f"  Documents indexed  : {stats.get('numberOfNewDocumentsIndexed', '?')}")
            print(f"  Documents failed   : {stats.get('numberOfDocumentsFailed', 0)}")
            break
        if status == "FAILED":
            print(f" FAILED")
            print(job.get("failureReasons", ""))
            sys.exit(1)
    else:
        print("\nTimeout — check ingestion status in AWS console.")

    return job_id


def main():
    print("=" * 60)
    print("Bedrock Knowledge Base Setup")
    print("=" * 60)

    if not S3_BUCKET_NAME:
        print("ERROR: S3_BUCKET_NAME not set"); sys.exit(1)
    if not OPENSEARCH_COLLECTION_ARN:
        print("ERROR: OPENSEARCH_COLLECTION_ARN not set")
        print("       Run: python scripts/setup_opensearch.py"); sys.exit(1)

    iam           = get_client("iam")
    bedrock_agent = get_client("bedrock-agent")

    role_arn      = get_role_arn(iam)
    kb_id, kb_arn = create_knowledge_base(bedrock_agent, role_arn)
    ds_id         = create_data_source(bedrock_agent, kb_id)
    start_ingestion(bedrock_agent, kb_id, ds_id)

    print("\nWriting IDs to .env ...")
    write_env("KNOWLEDGE_BASE_ID",  kb_id)
    write_env("KNOWLEDGE_BASE_ARN", kb_arn)

    print("\n" + "=" * 60)
    print("Knowledge Base setup complete!")
    print(f"  KNOWLEDGE_BASE_ID  = {kb_id}")
    print(f"  KNOWLEDGE_BASE_ARN = {kb_arn}")
    print("\nLaunch the app:")
    print("  streamlit run app/main.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
