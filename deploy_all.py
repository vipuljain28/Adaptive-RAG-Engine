"""
deploy_all.py — Single-Command Master Deployment Script

Usage:
    python deploy_all.py
"""
import os
import sys

# Delegate directly to scripts/deploy_all.py
script_path = os.path.join(os.path.dirname(__file__), "scripts", "deploy_all.py")
os.execv(sys.executable, [sys.executable, script_path])
