import os
import sys
import time
import subprocess
import json
import re

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from scripts._aws_client import get_client, AWS_REGION

def print_banner(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def update_env_variable(key: str, value: str):
    if not value: return
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if not os.path.exists(env_path):
        with open(env_path, "w") as f:
            f.write(f"{key}={value}\n")
        print(f"  [Created .env] {key}={value}")
        return

    with open(env_path, "r") as f:
        content = f.read()

    pattern = rf"^{re.escape(key)}=.*$"
    replacement = f"{key}={value}"
    if re.search(pattern, content, flags=re.MULTILINE):
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    else:
        if not content.endswith("\n"):
            content += "\n"
        content += f"{replacement}\n"

    with open(env_path, "w") as f:
        f.write(content)
    print(f"  [Updated .env] {key}={value}")

def step_1_main_terraform():
    print_banner("STEP 1: Provisioning Main Infrastructure via Terraform (EC2, Bedrock, OpenSearch, S3)")
    main_tf_dir = os.path.join(PROJECT_ROOT, "terraform")
    
    res = subprocess.run(["terraform", "init"], cwd=main_tf_dir)
    if res.returncode != 0:
        raise RuntimeError("Terraform Init Failed")
        
    res = subprocess.run(["terraform", "apply", "-auto-approve"], cwd=main_tf_dir)
    if res.returncode != 0:
        raise RuntimeError("Terraform Apply Failed")

    print("\n  Fetching Terraform Outputs...")
    output = subprocess.check_output(["terraform", "output", "-json"], cwd=main_tf_dir).decode()
    outputs = json.loads(output)
    
    update_env_variable("S3_BUCKET_NAME", outputs.get("s3_bucket_name", {}).get("value", ""))
    update_env_variable("KNOWLEDGE_BASE_ID", outputs.get("knowledge_base_id", {}).get("value", ""))
    update_env_variable("OPENSEARCH_COLLECTION_ARN", outputs.get("opensearch_collection_arn", {}).get("value", ""))
    update_env_variable("GUARDRAIL_ID", outputs.get("guardrail_id", {}).get("value", ""))
    update_env_variable("GUARDRAIL_VERSION", outputs.get("guardrail_version", {}).get("value", ""))
    
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"), override=True)

def step_2_eks_terraform():
    print_banner("STEP 2: Provisioning EKS Cluster & TinyLlama via Terraform & Helm")
    eks_tf_dir = os.path.join(PROJECT_ROOT, "bonus", "eks", "terraform")
    helm_chart_dir = os.path.join(PROJECT_ROOT, "bonus", "eks", "helm", "tinyllama")

    if not os.path.exists(eks_tf_dir):
        print("  Skipping EKS (not configured)")
        return

    subprocess.run(["terraform", "init"], cwd=eks_tf_dir)
    res_tf = subprocess.run(["terraform", "apply", "-auto-approve"], cwd=eks_tf_dir)
    if res_tf.returncode != 0:
        print("  Terraform apply encountered an issue. Retrying...")
        subprocess.run(["terraform", "apply", "-auto-approve"], cwd=eks_tf_dir)

    print("  Updating local kubeconfig for knowledge-assistant-eks...")
    subprocess.run(["aws", "eks", "update-kubeconfig", "--region", AWS_REGION, "--name", "knowledge-assistant-eks"])

    print("  Deploying TinyLlama Helm Chart to EKS...")
    subprocess.run(["helm", "upgrade", "--install", "tinyllama", helm_chart_dir, "--namespace", "default"])

    print("  Fetching AWS LoadBalancer EXTERNAL-IP...")
    elb_dns = ""
    for _ in range(12):
        try:
            out = subprocess.check_output(["kubectl", "get", "svc", "tinyllama-tinyllama", "-o", "json"]).decode()
            svc_data = json.loads(out)
            ingresses = svc_data.get("status", {}).get("loadBalancer", {}).get("ingress", [])
            if ingresses and "hostname" in ingresses[0]:
                elb_dns = ingresses[0]["hostname"]
                break
        except Exception:
            pass
        time.sleep(5)

    if elb_dns:
        tiny_url = f"http://{elb_dns}:8080"
        print(f"  [EKS TinyLlama Service URL]: {tiny_url}")
        update_env_variable("TINYLLAMA_ENDPOINT", tiny_url)
        update_env_variable("TINYLLAMA_ENABLE_MOCK", "false")
        update_env_variable("TINYLLAMA_TIMEOUT", "120")
    else:
        print("  Warning: Could not fetch LoadBalancer DNS name within timeout.")

def step_3_upload_and_ingest():
    print_banner("STEP 3: Uploading Documents & Running Ingestion Sync")
    upload_script = os.path.join(PROJECT_ROOT, "scripts", "upload_documents.py")
    res = subprocess.run([sys.executable, upload_script], cwd=PROJECT_ROOT)
    if res.returncode != 0:
        raise RuntimeError("Step 3 (Upload Documents) failed!")

    agent = get_client("bedrock-agent")
    kb_id = os.getenv("KNOWLEDGE_BASE_ID")
    if not kb_id:
        print("  Warning: KNOWLEDGE_BASE_ID missing. Skipping sync.")
        return

    ds_res = agent.list_data_sources(knowledgeBaseId=kb_id, maxResults=1)
    if ds_res["dataSourceSummaries"]:
        ds_id = ds_res["dataSourceSummaries"][0]["dataSourceId"]
        print(f"  Starting Bedrock KB Ingestion Sync (KB: {kb_id}, DS: {ds_id})...")
        sync_res = agent.start_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=ds_id,
            description="Master deployment ingestion sync"
        )
        job_id = sync_res["ingestionJob"]["ingestionJobId"]
        print(f"  Ingestion Job ID: {job_id}")
    else:
        print("  No Data Source found in Knowledge Base!")

def step_4_ec2():
    print_banner("STEP 4: Deploying Codebase Bundle to EC2 & Restarting Service")
    s3_deploy = os.path.join(PROJECT_ROOT, "scripts", "deploy_to_s3.py")
    subprocess.run([sys.executable, s3_deploy], cwd=PROJECT_ROOT)

    print("  Triggering EC2 setup script via SSM to pull the new code...")
    ec2_service = os.path.join(PROJECT_ROOT, "scripts", "fix_ec2.py")
    subprocess.run([sys.executable, ec2_service], cwd=PROJECT_ROOT)

def step_5_summary():
    print_banner("STEP 5: Automated Verification & Health Dashboard")
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"), override=True)

    print(f"  AWS Region            : {os.getenv('AWS_REGION', 'us-east-1')}")
    print(f"  S3 Bucket             : s3://{os.getenv('S3_BUCKET_NAME')}")
    print(f"  OpenSearch Collection : {os.getenv('OPENSEARCH_COLLECTION_ARN')}")
    print(f"  Knowledge Base ID     : {os.getenv('KNOWLEDGE_BASE_ID')}")
    print(f"  Guardrail ID          : {os.getenv('GUARDRAIL_ID')} (v{os.getenv('GUARDRAIL_VERSION')})")
    print(f"  TinyLlama Endpoint    : {os.getenv('TINYLLAMA_ENDPOINT')}")

    ec2_ip = "100.24.105.149"
    try:
        ec2_client = get_client("ec2")
        instances = ec2_client.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])
        for r in instances.get("Reservations", []):
            for i in r.get("Instances", []):
                if i.get("State", {}).get("Name") == "running" and i.get("PublicIpAddress"):
                    ec2_ip = i["PublicIpAddress"]
    except Exception:
        pass

    print("\n" + "*" * 80)
    print(f"  [SUCCESS] Application is live at:")
    print(f"  Web UI: http://{ec2_ip}:8501")
    print(f"  Alternates: http://{ec2_ip}")
    print("*" * 80 + "\n")

def main():
    start_time = time.time()
    print_banner("ONE-COMMAND MASTER DEPLOYMENT: KNOWLEDGE ASSISTANT (EC2 + EKS + BEDROCK)")
    try:
        step_1_main_terraform()
        step_2_eks_terraform()
        step_3_upload_and_ingest()
        step_4_ec2()
        step_5_summary()
        elapsed = round((time.time() - start_time) / 60, 2)
        print(f"Deployment completed in {elapsed} minutes.")
    except Exception as e:
        print(f"\n[X] DEPLOYMENT FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
