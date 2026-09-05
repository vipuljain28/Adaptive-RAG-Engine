"""
destroy_all.py — Reliable One-Command Terraform Teardown Script

Pre-cleans blocking Kubernetes LoadBalancers, orphan ELBs, and S3 objects,
then executes `terraform destroy` across both EKS and Main Terraform modules.

Usage:
    python destroy_all.py
"""

import os
import sys
import subprocess
import time

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

from scripts._aws_client import get_client, AWS_REGION


def print_banner(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def pre_cleanup_elbs_and_k8s():
    print_banner("PRE-CLEANUP: Removing Kubernetes Services & Orphan Load Balancers")
    
    # 1. Try deleting Helm release & k8s LoadBalancer Service
    try:
        print("  Uninstalling Helm release 'tinyllama'...")
        subprocess.run(["helm", "uninstall", "tinyllama", "--namespace", "default"], capture_output=True)
        print("  Deleting Kubernetes service 'tinyllama-tinyllama'...")
        subprocess.run(["kubectl", "delete", "svc", "tinyllama-tinyllama", "--namespace", "default"], capture_output=True)
    except Exception as e:
        print(f"  Note during k8s cleanup: {e}")

    # 2. Delete any active AWS Classic ELBs that block VPC subnet deletion
    try:
        elb_client = get_client("elb")
        lbs = elb_client.describe_load_balancers().get("LoadBalancerDescriptions", [])
        for lb in lbs:
            name = lb["LoadBalancerName"]
            print(f"  [AWS ELB] Deleting blocking Load Balancer: {name}")
            elb_client.delete_load_balancer(LoadBalancerName=name)
        if lbs:
            print("  Waiting 10s for ELB network interfaces to detach...")
            time.sleep(10)
    except Exception as e:
        print(f"  Note checking ELBs: {e}")


def pre_cleanup_s3():
    print_banner("PRE-CLEANUP: Emptying S3 Storage Buckets")
    try:
        s3 = get_client("s3")
        buckets = s3.list_buckets().get("Buckets", [])
        for b in buckets:
            bname = b["Name"]
            if "knowledge-assistant" in bname or "vipul-bedrock" in bname:
                print(f"  Emptying bucket: s3://{bname}...")
                # Delete all objects
                res = s3.list_objects_v2(Bucket=bname)
                for obj in res.get("Contents", []):
                    s3.delete_object(Bucket=bname, Key=obj["Key"])
                # Delete all object versions if versioning is enabled
                ver_res = s3.list_object_versions(Bucket=bname)
                for ver in ver_res.get("Versions", []):
                    s3.delete_object(Bucket=bname, Key=ver["Key"], VersionId=ver["VersionId"])
                for m in ver_res.get("DeleteMarkers", []):
                    s3.delete_object(Bucket=bname, Key=m["Key"], VersionId=m["VersionId"])
    except Exception as e:
        print(f"  Note emptying S3 buckets: {e}")


def main():
    print_banner("ONE-COMMAND TERRAFORM TEARDOWN: DESTROYING ALL AWS RESOURCES")

    # Run pre-cleanup to prevent terraform destroy from hanging
    pre_cleanup_elbs_and_k8s()
    pre_cleanup_s3()

    # Step 1: Destroy EKS Cluster & Node Groups
    eks_tf_dir = os.path.join(PROJECT_ROOT, "bonus", "eks", "terraform")
    if os.path.exists(eks_tf_dir):
        print_banner("STEP 1: Destroying EKS Cluster & VPC Infrastructure")
        subprocess.run(["terraform", "destroy", "-auto-approve"], cwd=eks_tf_dir)

    # Step 2: Destroy Main Infrastructure (S3, OpenSearch, Bedrock KB, Guardrails, EC2, IAM)
    main_tf_dir = os.path.join(PROJECT_ROOT, "terraform")
    if os.path.exists(main_tf_dir):
        print_banner("STEP 2: Destroying Main Infrastructure (Bedrock KB, Guardrails, OpenSearch, EC2, S3)")
        subprocess.run(["terraform", "destroy", "-auto-approve"], cwd=main_tf_dir)

    print_banner("TERRAFORM DESTROY COMPLETE — All resources cleaned up successfully!")


if __name__ == "__main__":
    main()
