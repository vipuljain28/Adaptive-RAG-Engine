"""
scripts/upload_documents.py — Upload sample documents to S3.

Usage:
    python scripts/upload_documents.py
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

from scripts._aws_client import get_client

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "")
DOCS_DIR       = os.path.join(os.path.dirname(__file__), "..", "sample_documents")
S3_PREFIX      = "documents/"
ALLOWED_EXT    = {".txt", ".pdf", ".md", ".docx"}


def main():
    if not S3_BUCKET_NAME:
        print("ERROR: S3_BUCKET_NAME not set in .env"); sys.exit(1)

    if not os.path.isdir(DOCS_DIR):
        print(f"ERROR: sample_documents/ not found at {DOCS_DIR}"); sys.exit(1)

    s3 = get_client("s3")

    files = [f for f in os.listdir(DOCS_DIR)
             if os.path.splitext(f.lower())[1] in ALLOWED_EXT]

    if not files:
        print("No documents found in sample_documents/"); sys.exit(0)

    print(f"Uploading {len(files)} file(s) to s3://{S3_BUCKET_NAME}/{S3_PREFIX}")
    print("-" * 60)

    success = 0
    for fname in sorted(files):
        local = os.path.join(DOCS_DIR, fname)
        key   = S3_PREFIX + fname
        size  = os.path.getsize(local)
        print(f"  {fname:40s} {size:>8,} bytes -> {key}")
        try:
            s3.upload_file(local, S3_BUCKET_NAME, key)
            success += 1
        except Exception as e:
            print(f"  ERROR: {e}")

    print("-" * 60)
    print(f"Done: {success}/{len(files)} uploaded.")
    if success > 0:
        print("\nNext: python scripts/setup_opensearch.py")


if __name__ == "__main__":
    main()
