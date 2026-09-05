import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts._aws_client import get_client

ssm = get_client('ssm')
ec2 = get_client('ec2')
instances = ec2.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])
instance_id = None
for r in instances.get("Reservations", []):
    for i in r.get("Instances", []):
        if i.get("State", {}).get("Name") == "running":
            instance_id = i["InstanceId"]
            break
if not instance_id:
    print("Could not find a running instance named 'knowledge-assistant-app'")
    sys.exit(1)

service_content = """[Unit]
Description=Knowledge Assistant Streamlit Service
After=network.target

[Service]
User=root
WorkingDirectory=/home/appuser/capstone
ExecStart=/home/appuser/capstone/venv/bin/python -m streamlit run app/main.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONPATH=/home/appuser/capstone

[Install]
WantedBy=multi-user.target
"""

script = f"""#!/bin/bash
useradd -m appuser || true
mkdir -p /home/appuser/capstone/data
cd /home/appuser/capstone
if [ ! -d "/home/appuser/capstone/venv" ]; then
    python3 -m venv /home/appuser/capstone/venv
    /home/appuser/capstone/venv/bin/pip install boto3
fi
/home/appuser/capstone/venv/bin/python -c "import boto3; boto3.client('s3', region_name='us-east-1').download_file('knowledge-assistant-docs-674959318309', 'deploy/app_deploy.zip', '/home/appuser/capstone/app_deploy.zip')"
rm -rf /home/appuser/capstone/app /home/appuser/capstone/observability /home/appuser/capstone/gateway /home/appuser/capstone/guardrails /home/appuser/capstone/prompts /home/appuser/capstone/scripts
unzip -o /home/appuser/capstone/app_deploy.zip
rm -f /home/appuser/capstone/app_deploy.zip
if [ ! -d "/home/appuser/capstone/venv" ]; then
    python3 -m venv /home/appuser/capstone/venv
fi
echo "/home/appuser/capstone" > /home/appuser/capstone/venv/lib/python3.9/site-packages/capstone.pth
echo "/home/appuser/capstone" > /home/appuser/capstone/venv/lib64/python3.9/site-packages/capstone.pth || true
rm -rf /home/appuser/capstone/venv/lib/python3.9/site-packages/app /home/appuser/capstone/venv/lib64/python3.9/site-packages/app || true
rm -rf /home/appuser/capstone/venv/lib/python3.9/site-packages/observability /home/appuser/capstone/venv/lib64/python3.9/site-packages/observability || true
rm -rf /home/appuser/capstone/venv/lib/python3.9/site-packages/gateway /home/appuser/capstone/venv/lib64/python3.9/site-packages/gateway || true
rm -rf /home/appuser/capstone/venv/lib/python3.9/site-packages/guardrails /home/appuser/capstone/venv/lib64/python3.9/site-packages/guardrails || true
/home/appuser/capstone/venv/bin/pip install streamlit boto3 python-dotenv pillow requests pydantic langfuse plotly pandas SpeechRecognition || true
chown -R appuser:appuser /home/appuser/capstone
cat << 'EOF' > /etc/systemd/system/knowledge-assistant.service
{service_content}
EOF
systemctl daemon-reload
systemctl enable knowledge-assistant
systemctl restart knowledge-assistant
sysctl -w net.ipv4.ip_forward=1
iptables -t nat -F PREROUTING
iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8501
"""

commands = [script]

print("  Waiting for instance to be registered in SSM...")
for _ in range(60):
    try:
        info = ssm.describe_instance_information(Filters=[{'Key': 'InstanceIds', 'Values': [instance_id]}])
        if info.get('InstanceInformationList'):
            print("  Instance is registered with SSM. Sending command...")
            break
    except Exception:
        pass
    time.sleep(5)
else:
    print("  WARNING: Instance not registered with SSM. Trying command anyway...")

res = ssm.send_command(
    InstanceIds=[instance_id],
    DocumentName='AWS-RunShellScript',
    Parameters={'commands': commands}
)
command_id = res['Command']['CommandId']
print("Command ID:", command_id)

time.sleep(12)
out = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
print("Status:", out.get('Status'))
print("STDOUT:\n", out.get('StandardOutputContent'))
print("STDERR:\n", out.get('StandardErrorContent'))
