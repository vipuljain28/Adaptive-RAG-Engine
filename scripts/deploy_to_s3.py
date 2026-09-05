import os
import zipfile
import boto3
from dotenv import load_dotenv

load_dotenv()

s3_bucket = os.getenv("S3_BUCKET_NAME", "knowledge-assistant-docs-674959318309")
zip_path = "app_deploy.zip"

print(f"Creating {zip_path}...")
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    # Folders to include
    folders_to_zip = ['app', 'bonus', 'gateway', 'guardrails', 'observability', 'prompts', 'scripts']
    for folder in folders_to_zip:
        if os.path.exists(folder):
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if not file.endswith('.pyc') and '__pycache__' not in root and '.terraform' not in root:
                        file_path = os.path.join(root, file)
                        try:
                            zipf.write(file_path, file_path)
                        except PermissionError:
                            print(f"Skipping locked file: {file_path}")

    # Individual files to include
    files_to_zip = ['requirements.txt', '.env']
    for file in files_to_zip:
        if os.path.exists(file):
            zipf.write(file, file)

print(f"Uploading {zip_path} to s3://{s3_bucket}/deploy/app_deploy.zip...")
s3 = boto3.client('s3', region_name=os.getenv("AWS_REGION", "us-east-1"))
s3.upload_file(zip_path, s3_bucket, "deploy/app_deploy.zip")
print("Upload successful!")
