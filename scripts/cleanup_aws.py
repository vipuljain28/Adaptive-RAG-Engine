#!/usr/bin/env python3
"""
cleanup_aws.py — Deletes all AWS resources created for the Knowledge Assistant capstone project.

Resources deleted (in dependency order):
  1. EC2 Instance (knowledge-assistant-app-dev)
  2. EC2 Security Group (knowledge-assistant-sg-dev)
  3. Bedrock Guardrail (knowledge-assistant-guardrail)
  4. Bedrock Knowledge Base data source (3BTPQGVBWX) from KB IY7GSOCYCH
  5. Bedrock Knowledge Base (IY7GSOCYCH)
  6. OpenSearch Serverless Collection (zrhy9hl9a0vtsgj4f0h — knowledge-assistant)
  7. S3 bucket contents + deploy prefix in (knowledge-assistant-docs-674959318309)
  8. IAM Role policies + roles created for the KB

Resources NOT deleted (pre-existing / shared):
  - S3 bucket itself (retained — may contain other data)
  - Other OpenSearch collections (knowledge-assistant-dev, bedrock-knowledge-base-hxnhid)
  - VPC vpc-031c0bbf0770403f6 (may be needed for re-deploy)
  - SageMaker roles
  - Other EC2 instances (t3.xlarge, windows_vipul)

Run:
  python scripts/cleanup_aws.py

Set DRY_RUN = True to preview without deleting.
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scripts._aws_client import get_client

DRY_RUN = False  # Set True to preview only

def log(msg):
    print(f"  {'[DRY-RUN] ' if DRY_RUN else ''}{msg}")

def confirm(prompt):
    ans = input(f"\n{prompt} [yes/no]: ").strip().lower()
    return ans == "yes"

# ─────────────────────────────────────────────────────────────
# 1. STOP & TERMINATE EC2 INSTANCE
# ─────────────────────────────────────────────────────────────
def terminate_ec2():
    ec2 = get_client("ec2")
    instance_id = "i-02d6f4514eb18b127"
    print(f"\n[1] EC2 Instance: {instance_id} (knowledge-assistant-app-dev)")
    if not DRY_RUN:
        ec2.terminate_instances(InstanceIds=[instance_id])
        log(f"Termination initiated for {instance_id}")
        # Wait for termination
        print("    Waiting for instance to terminate (up to 3 minutes)...")
        waiter = ec2.get_waiter("instance_terminated")
        try:
            waiter.wait(InstanceIds=[instance_id], WaiterConfig={"Delay": 15, "MaxAttempts": 12})
            log(f"Instance {instance_id} terminated.")
        except Exception as e:
            log(f"Waiter error (may still be terminating): {e}")
    else:
        log(f"Would terminate EC2 instance {instance_id}")

# ─────────────────────────────────────────────────────────────
# 2. DELETE SECURITY GROUP
# ─────────────────────────────────────────────────────────────
def delete_security_group():
    ec2 = get_client("ec2")
    sg_id = "sg-012e4a535cabeca66"
    print(f"\n[2] Security Group: {sg_id} (knowledge-assistant-sg-dev)")
    if not DRY_RUN:
        time.sleep(10)  # Allow EC2 to finish detaching
        try:
            ec2.delete_security_group(GroupId=sg_id)
            log(f"Security group {sg_id} deleted.")
        except Exception as e:
            log(f"Error deleting SG (may still be in use): {e}")
    else:
        log(f"Would delete security group {sg_id}")

# ─────────────────────────────────────────────────────────────
# 3. DELETE BEDROCK GUARDRAIL
# ─────────────────────────────────────────────────────────────
def delete_guardrail():
    bedrock = get_client("bedrock")
    guardrail_id = "epexi952sjix"
    print(f"\n[3] Bedrock Guardrail: {guardrail_id} (knowledge-assistant-guardrail)")
    if not DRY_RUN:
        try:
            bedrock.delete_guardrail(guardrailIdentifier=guardrail_id)
            log(f"Guardrail {guardrail_id} deleted.")
        except Exception as e:
            log(f"Error: {e}")
    else:
        log(f"Would delete Bedrock Guardrail {guardrail_id}")

# ─────────────────────────────────────────────────────────────
# 4. DELETE BEDROCK KNOWLEDGE BASE DATA SOURCE
# ─────────────────────────────────────────────────────────────
def delete_kb_data_source():
    bedrock_agent = get_client("bedrock-agent")
    kb_id = "IY7GSOCYCH"
    ds_id = "3BTPQGVBWX"
    print(f"\n[4] Bedrock KB Data Source: {ds_id} from KB {kb_id}")
    if not DRY_RUN:
        try:
            bedrock_agent.delete_data_source(knowledgeBaseId=kb_id, dataSourceId=ds_id)
            log(f"Data source {ds_id} deleted.")
            time.sleep(5)
        except Exception as e:
            log(f"Error: {e}")
    else:
        log(f"Would delete KB data source {ds_id}")

# ─────────────────────────────────────────────────────────────
# 5. DELETE BEDROCK KNOWLEDGE BASE
# ─────────────────────────────────────────────────────────────
def delete_knowledge_base():
    bedrock_agent = get_client("bedrock-agent")
    kb_id = "IY7GSOCYCH"
    print(f"\n[5] Bedrock Knowledge Base: {kb_id} (vipul-knowledge-base-quick-start-5cyu0)")
    if not DRY_RUN:
        try:
            bedrock_agent.delete_knowledge_base(knowledgeBaseId=kb_id)
            log(f"Knowledge base {kb_id} deleted.")
            time.sleep(10)
        except Exception as e:
            log(f"Error: {e}")
    else:
        log(f"Would delete Knowledge Base {kb_id}")

# ─────────────────────────────────────────────────────────────
# 6. DELETE OPENSEARCH SERVERLESS COLLECTION
# ─────────────────────────────────────────────────────────────
def delete_opensearch_collection():
    aoss = get_client("opensearchserverless")
    collection_id = "zrhy9hl9a0vtsgj4f0h"
    print(f"\n[6] OpenSearch Serverless Collection: {collection_id} (knowledge-assistant)")
    if not DRY_RUN:
        try:
            aoss.delete_collection(id=collection_id)
            log(f"OpenSearch collection {collection_id} deletion initiated.")
            time.sleep(15)
        except Exception as e:
            log(f"Error: {e}")
    else:
        log(f"Would delete OpenSearch Serverless collection {collection_id}")

# ─────────────────────────────────────────────────────────────
# 7. CLEAR S3 DEPLOY PREFIX (keep bucket + documents)
# ─────────────────────────────────────────────────────────────
def clear_s3_deploy():
    s3 = get_client("s3")
    bucket = "knowledge-assistant-docs-674959318309"
    prefix = "deploy/"
    print(f"\n[7] S3 Deploy Objects: s3://{bucket}/{prefix}")
    if not DRY_RUN:
        try:
            objs = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
            for obj in objs.get("Contents", []):
                s3.delete_object(Bucket=bucket, Key=obj["Key"])
                log(f"Deleted: s3://{bucket}/{obj['Key']}")
        except Exception as e:
            log(f"Error: {e}")
    else:
        log(f"Would delete deploy/ objects from s3://{bucket}/")

# ─────────────────────────────────────────────────────────────
# 8. DELETE IAM ROLES CREATED FOR KB
# ─────────────────────────────────────────────────────────────
def delete_iam_roles():
    iam = get_client("iam")
    roles_to_delete = [
        "AmazonBedrockExecutionRoleForKnowledgeBase_5cyu0",
        "AmazonBedrockExecutionRoleForKnowledgeBase_sva4q",
        "AmazonBedrockExecutionRoleForKnowledgeBase_w8675",
    ]
    print(f"\n[8] IAM Roles: {len(roles_to_delete)} Bedrock KB execution roles")
    for role_name in roles_to_delete:
        if not DRY_RUN:
            try:
                # Detach all managed policies
                attached = iam.list_attached_role_policies(RoleName=role_name)
                for pol in attached.get("AttachedPolicies", []):
                    iam.detach_role_policy(RoleName=role_name, PolicyArn=pol["PolicyArn"])
                    log(f"  Detached policy {pol['PolicyArn']} from {role_name}")
                # Delete inline policies
                inlines = iam.list_role_policies(RoleName=role_name)
                for pol_name in inlines.get("PolicyNames", []):
                    iam.delete_role_policy(RoleName=role_name, PolicyName=pol_name)
                    log(f"  Deleted inline policy {pol_name} from {role_name}")
                iam.delete_role(RoleName=role_name)
                log(f"Role {role_name} deleted.")
            except Exception as e:
                log(f"  Error deleting {role_name}: {e}")
        else:
            log(f"Would delete IAM role: {role_name}")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  Knowledge Assistant — AWS Cleanup Script")
    print("=" * 60)
    print()
    print("Resources to be DELETED:")
    print("  1. EC2 i-02d6f4514eb18b127  (knowledge-assistant-app-dev)")
    print("  2. SG  sg-012e4a535cabeca66 (knowledge-assistant-sg-dev)")
    print("  3. Guardrail epexi952sjix   (knowledge-assistant-guardrail)")
    print("  4. KB Data Source 3BTPQGVBWX")
    print("  5. Knowledge Base IY7GSOCYCH")
    print("  6. OpenSearch Collection zrhy9hl9a0vtsgj4f0h")
    print("  7. S3 deploy/ prefix objects")
    print("  8. IAM Roles (3 Bedrock KB execution roles)")
    print()
    print("Resources PRESERVED:")
    print("  - S3 bucket (knowledge-assistant-docs-674959318309)")
    print("  - S3 documents/ prefix")
    print("  - VPC vpc-031c0bbf0770403f6 (for re-deploy)")
    print("  - Other EC2 instances (t3.xlarge, windows_vipul)")
    print("  - Other OpenSearch collections")
    print()

    if DRY_RUN:
        print(">>> DRY-RUN MODE — no resources will be deleted <<<")
    else:
        if not confirm("Are you sure you want to delete all these resources?"):
            print("Aborted.")
            return

    terminate_ec2()
    delete_security_group()
    delete_guardrail()
    delete_kb_data_source()
    delete_knowledge_base()
    delete_opensearch_collection()
    clear_s3_deploy()
    delete_iam_roles()

    print()
    print("=" * 60)
    print("  Cleanup complete!")
    print("=" * 60)
    print()
    print("To re-deploy when ready:")
    print("  1. python scripts/setup_ec2.py")
    print("  2. python scripts/setup_knowledge_base.py")
    print("  3. python guardrails/setup_guardrail.py")
    print("  4. python scripts/deploy_to_s3.py")
    print("  5. python scripts/setup_ec2_service.py")


if __name__ == "__main__":
    main()
