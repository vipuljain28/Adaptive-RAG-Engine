"""
scripts/setup_s3.py — Create the S3 bucket for Knowledge Assistant documents.

Usage:
    python scripts/setup_s3.py
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

from scripts._aws_client import get_client, AWS_REGION

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "")


def main():
    if not S3_BUCKET_NAME:
        print("ERROR: S3_BUCKET_NAME not set in .env"); sys.exit(1)

    s3 = get_client("s3")

    # Check if already exists
    try:
        s3.head_bucket(Bucket=S3_BUCKET_NAME)
        print(f"Bucket already exists: {S3_BUCKET_NAME} — skipping creation.")
    except Exception as e:
        code = getattr(e, "response", {}).get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchBucket", "NoSuchKey") or "404" in str(e):
            print(f"Creating bucket: {S3_BUCKET_NAME} in {AWS_REGION} ...")
            if AWS_REGION == "us-east-1":
                s3.create_bucket(Bucket=S3_BUCKET_NAME)
            else:
                s3.create_bucket(
                    Bucket=S3_BUCKET_NAME,
                    CreateBucketConfiguration={"LocationConstraint": AWS_REGION},
                )
            print("  Bucket created.")
        else:
            raise

    # Versioning
    s3.put_bucket_versioning(
        Bucket=S3_BUCKET_NAME,
        VersioningConfiguration={"Status": "Enabled"},
    )
    print("  Versioning enabled.")

    # Block public access
    s3.put_public_access_block(
        Bucket=S3_BUCKET_NAME,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True, "IgnorePublicAcls": True,
            "BlockPublicPolicy": True, "RestrictPublicBuckets": True,
        },
    )
    print("  Public access blocked.")

    # Encryption
    s3.put_bucket_encryption(
        Bucket=S3_BUCKET_NAME,
        ServerSideEncryptionConfiguration={"Rules": [{
            "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}
        }]},
    )
    print("  AES-256 encryption enabled.")

    print(f"\nDone! Bucket: {S3_BUCKET_NAME}")
    print(f"ARN: arn:aws:s3:::{S3_BUCKET_NAME}")
    print("\nNext: python scripts/upload_documents.py")


if __name__ == "__main__":
    main()
