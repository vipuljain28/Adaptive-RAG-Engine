"""
Shared boto3 client factory for all setup scripts.
Uses verify=False to bypass SSL certificate issues on corporate networks.
Import get_client() in every setup script instead of calling boto3.client() directly.
"""

import boto3
import urllib3
import warnings

# Suppress InsecureRequestWarning printed by urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore")

# Single source for region — scripts import this too
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

AWS_REGION     = os.getenv("AWS_REGION",     "us-east-1")
AWS_ACCOUNT_ID = os.getenv("AWS_ACCOUNT_ID", "674959318309")


def get_client(service: str, region: str = None) -> boto3.client:
    """Return a boto3 client with SSL verification disabled."""
    return boto3.client(service, region_name=region or AWS_REGION, verify=False)


def get_resource(service: str, region: str = None):
    """Return a boto3 resource with SSL verification disabled."""
    return boto3.resource(service, region_name=region or AWS_REGION, verify=False)
