"""
scripts/create_deploy_zip.py
Creates a deployment zip of the application code and uploads it to S3.
The EC2 user_data.sh pulls this zip on first boot.

Usage:
    python scripts/create_deploy_zip.py

Output:
    dist/app_deploy.zip  (local)
    s3://knowledge-assistant-docs-674959318309/deploy/app_deploy.zip  (remote)
"""

import os, sys, zipfile, shutil, warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

from scripts._aws_client import get_client

BASE    = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTDIR  = os.path.join(BASE, "dist")
ZIPPATH = os.path.join(OUTDIR, "app_deploy.zip")

S3_BUCKET = os.getenv("S3_BUCKET_NAME", "knowledge-assistant-docs-674959318309")
S3_KEY    = "deploy/app_deploy.zip"

# Folders/files to include in the zip
INCLUDE_DIRS = [
    "app",
    "gateway",
    "guardrails",
    "observability",
    "sample_documents",
    "scripts",
]
INCLUDE_FILES = [
    "requirements.txt",
    "run.sh",
    ".env",         # EC2 needs the env vars (KB ID, guardrail ID, etc.)
]

# Patterns to exclude even if inside an included folder
EXCLUDE_PATTERNS = [
    "__pycache__",
    ".pyc",
    ".pyo",
    "test_routing_out",
    "test_routing_err",
    "aoss_out",
    "aoss_err",
    "gen_result",
    "gen_out",
    "gen_err",
    "doc_gen",
    "dist",
    ".terraform",
    ".tfstate",
    ".tfvars",
    "node_modules",
    ".git",
    "data/conversations.db",
]


def should_exclude(path: str) -> bool:
    for pat in EXCLUDE_PATTERNS:
        if pat in path:
            return True
    return False


def create_zip():
    os.makedirs(OUTDIR, exist_ok=True)
    if os.path.exists(ZIPPATH):
        os.remove(ZIPPATH)

    added = 0
    with zipfile.ZipFile(ZIPPATH, "w", zipfile.ZIP_DEFLATED) as zf:

        # Add directories
        for folder in INCLUDE_DIRS:
            folder_abs = os.path.join(BASE, folder)
            if not os.path.exists(folder_abs):
                print(f"  SKIP (not found): {folder}/")
                continue
            for root, dirs, files in os.walk(folder_abs):
                # Prune excluded dirs in-place
                dirs[:] = [d for d in dirs
                           if not should_exclude(os.path.join(root, d))]
                for fname in files:
                    fpath = os.path.join(root, fname)
                    if should_exclude(fpath):
                        continue
                    arcname = os.path.relpath(fpath, BASE)
                    zf.write(fpath, arcname)
                    added += 1

        # Add root-level files
        for fname in INCLUDE_FILES:
            fpath = os.path.join(BASE, fname)
            if os.path.exists(fpath):
                zf.write(fpath, fname)
                added += 1
            else:
                print(f"  SKIP (not found): {fname}")

    size_mb = os.path.getsize(ZIPPATH) / (1024 * 1024)
    print(f"  Created: {ZIPPATH}")
    print(f"  Files  : {added}")
    print(f"  Size   : {size_mb:.2f} MB")
    return ZIPPATH


def upload_to_s3(zip_path: str):
    s3 = get_client("s3")
    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"\n  Uploading to s3://{S3_BUCKET}/{S3_KEY}  ({size_mb:.2f} MB)...")
    s3.upload_file(zip_path, S3_BUCKET, S3_KEY)
    print(f"  Upload complete.")
    url = f"https://{S3_BUCKET}.s3.amazonaws.com/{S3_KEY}"
    print(f"  S3 URL : {url}")


def main():
    print("=" * 60)
    print("Step 1: Creating deployment zip")
    print("=" * 60)
    zip_path = create_zip()

    print("\n" + "=" * 60)
    print("Step 2: Uploading to S3")
    print("=" * 60)
    upload_to_s3(zip_path)

    print("\nDone. EC2 user_data.sh will pull this zip on first boot.")


if __name__ == "__main__":
    main()
