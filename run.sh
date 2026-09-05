#!/bin/bash
# Startup script for EC2 deployment
# Run after cloning the repo and copying .env.template to .env

set -e

cd /home/ec2-user/capstone
source venv/bin/activate

echo "Starting Knowledge Assistant on port 8501..."
streamlit run app/main.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true
