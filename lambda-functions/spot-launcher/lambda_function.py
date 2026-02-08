import json
import boto3
import os
import base64
import logging
import time

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Lambda function to launch spot instances for parliament data import
    """
    try:
        # Get configuration from environment variables and event
        import_mode = os.environ.get('IMPORT_AUTOMATION_MODE', 'manual')
        instance_type = os.environ.get('SPOT_INSTANCE_TYPE', 't3.medium')  # 2 vCPUs, 4 GB RAM
        timeout_minutes = int(os.environ.get('IMPORT_TIMEOUT_MINUTES', '30'))
        
        # Check if event specifies a mode (discovery or importer)
        operation_mode = 'discovery'  # default mode
        if event and 'mode' in event:
            operation_mode = event.get('mode', 'discovery')
        elif event and 'body' in event:
            # Handle API Gateway body
            try:
                body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
                operation_mode = body.get('mode', 'discovery')
            except:
                pass
        
        logger.info(f"Starting spot instance launcher with automation mode: {import_mode}, operation mode: {operation_mode}")
        
        if import_mode == 'disabled':
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Import automation is disabled',
                    'mode': import_mode
                })
            }
        
        # Initialize EC2 client
        ec2 = boto3.client('ec2')
        
        # Create user data script for the spot instance
        user_data_script = f"""#!/bin/bash
# Parliament Data Import Script
yum update -y
yum install -y python3 python3-pip git postgresql15 unzip nc bind-utils

# Install AWS CLI v2 to avoid python dependency issues
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install
rm -rf aws awscliv2.zip

# Install and configure CloudWatch Logs agent
yum install -y amazon-cloudwatch-agent

# Get instance ID for log stream naming
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
echo "Instance ID: $INSTANCE_ID"

# Create CloudWatch agent config with dynamic instance ID
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << CWCONFIG
{{
    "logs": {{
        "logs_collected": {{
            "files": {{
                "collect_list": [
                    {{
                        "file_path": "/var/log/parliament-import.log",
                        "log_group_name": "/aws/parliament/import",
                        "log_stream_name": "$INSTANCE_ID-parliament-import"
                    }}
                ]
            }}
        }}
    }}
}}
CWCONFIG

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s

# Wait a moment for agent to initialize
sleep 5

# Set environment variables
export PYTHONPATH="/parliament"
export AWS_DEFAULT_REGION="eu-west-1"
export DATABASE_SECRET_ARN="{os.environ.get('DATABASE_SECRET_ARN', '')}"
export IMPORT_TIMEOUT_MINUTES="{timeout_minutes}"

# Log everything to the CloudWatch log file
exec > >(tee -a /var/log/parliament-import.log)
exec 2>&1

# Also send initial messages to CloudWatch
echo "=== PARLIAMENT DATA IMPORT STARTING ===" | tee -a /var/log/parliament-import.log

echo "Starting Parliament data import at $(date)"
echo "Instance type: {instance_type}"
echo "Operation mode: {operation_mode}"
echo "Timeout: {timeout_minutes} minutes"

# Setup SSH key for GitHub access
echo "Setting up SSH key for GitHub repository access..."
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Get SSH deploy key from Secrets Manager (stored as plain text)
echo "Retrieving SSH deploy key from Secrets Manager..."
PRIVATE_KEY=$(aws secretsmanager get-secret-value --secret-id fiscaliza-prod-github-deploy-key --region eu-west-1 --query SecretString --output text)

# Setup SSH key
echo "$PRIVATE_KEY" > ~/.ssh/id_rsa
chmod 600 ~/.ssh/id_rsa

# Add GitHub to known hosts to avoid SSH prompt
ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null

# Clone parliament repository from GitHub
echo "Cloning parliament repository from GitHub..."
cd /
git clone git@github.com:rfsbraz/parliament.git || {{
    echo "Failed to clone repository via SSH, trying HTTPS fallback..."
    git clone https://github.com/rfsbraz/parliament.git || {{
        echo "Failed to clone repository completely, creating placeholder"
        mkdir -p /parliament/scripts/data_processing
        cd /parliament
        exit 1
    }}
}}

cd parliament

# Install Python dependencies with explicit boto3 first  
echo "Installing core dependencies first..."
pip3 install --upgrade pip
pip3 install boto3 psycopg2-binary python-dotenv

# Create necessary __init__.py files for Python modules
echo "Creating Python module structure..."
touch __init__.py
touch scripts/__init__.py
touch scripts/data_processing/__init__.py
touch scripts/data_processing/mappers/__init__.py
touch database/__init__.py

# Install Python dependencies from requirements.txt
if [ -f requirements.txt ]; then
    echo "Installing Python dependencies from requirements.txt..."
    # Use --ignore-installed to bypass RPM-installed package conflicts
    pip3 install --ignore-installed -r requirements.txt
    echo "Installing additional dependencies for spot instances..."
    pip3 install --ignore-installed rich alembic beautifulsoup4 lxml
else
    echo "No requirements.txt found, installing basic dependencies..."
    pip3 install --ignore-installed requests beautifulsoup4 lxml sqlalchemy flask rich alembic
fi

# Debug: Show installed packages
echo "=== INSTALLED PACKAGES ==="
pip3 list | grep -E "(boto3|psycopg2|python-dotenv)"
echo "=== PYTHON PATH ==="
python3 -c "import sys; print('\\n'.join(sys.path))"

# Test network connectivity to RDS
echo "=== TESTING NETWORK CONNECTIVITY ==="

# First test: Get RDS endpoint from Secrets Manager
echo "Testing AWS CLI Secrets Manager access..."
SECRET_JSON=$(aws secretsmanager get-secret-value --secret-id "{os.environ.get('DATABASE_SECRET_ARN', '')}" --region eu-west-1 --query SecretString --output text 2>&1)
if [ $? -eq 0 ]; then
    echo "✓ AWS CLI Secrets Manager call successful"
    RDS_HOST=$(echo "$SECRET_JSON" | python3 -c "import json, sys; data=json.load(sys.stdin); host=data.get('host',''); print(host.split(':')[0] if ':' in host else host)")
    RDS_PORT=$(echo "$SECRET_JSON" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('port', 5432))")
    echo "✓ Parsed RDS Host: $RDS_HOST"
    echo "✓ Parsed RDS Port: $RDS_PORT"
else
    echo "✗ AWS CLI Secrets Manager call failed: $SECRET_JSON"
    echo "Fallback: Using hardcoded RDS endpoint for connectivity test"
    RDS_HOST="fiscaliza-prod-postgres.ckubn9xqxngq.eu-west-1.rds.amazonaws.com"
    RDS_PORT="5432"
fi

# Test DNS resolution
echo "Testing DNS resolution for $RDS_HOST..."
if command -v nslookup >/dev/null 2>&1; then
    RDS_IP=$(nslookup $RDS_HOST | grep -A1 "Name:" | grep "Address:" | cut -d' ' -f2 | head -1)
    if [ -n "$RDS_IP" ]; then
        echo "✓ DNS resolution successful: $RDS_HOST -> $RDS_IP"
    else
        echo "✗ DNS resolution failed for $RDS_HOST"
    fi
else
    echo "✗ nslookup command not available"
fi

# Test network connectivity with nc (netcat)
echo "Testing port $RDS_PORT connectivity to $RDS_HOST..."
if [ -n "$RDS_HOST" ]; then
    timeout 5 nc -zv $RDS_HOST $RDS_PORT 2>&1 && echo "✓ Port $RDS_PORT is reachable" || echo "✗ Port $RDS_PORT is NOT reachable"
else
    echo "✗ Cannot test connectivity - RDS_HOST is empty"
fi

# Show network configuration
echo "=== NETWORK CONFIGURATION ==="
echo "Network interfaces:"
ip addr show
echo "Routing table:"
ip route show
echo "Security groups:"
curl -s http://169.254.169.254/latest/meta-data/security-groups
echo "Instance subnet info:"
curl -s http://169.254.169.254/latest/meta-data/network/interfaces/macs/$(curl -s http://169.254.169.254/latest/meta-data/network/interfaces/macs/)/subnet-id
echo "VPC info:"
curl -s http://169.254.169.254/latest/meta-data/network/interfaces/macs/$(curl -s http://169.254.169.254/latest/meta-data/network/interfaces/macs/)/vpc-id

# Test connectivity to known working endpoints
echo "=== CONNECTIVITY TESTS ==="
echo "Testing connectivity to AWS API (should work):"
timeout 3 nc -zv secretsmanager.eu-west-1.amazonaws.com 443 2>&1 && echo "✓ AWS API reachable" || echo "✗ AWS API not reachable"

echo "Testing connectivity to public DNS (should work):"
timeout 3 nc -zv 8.8.8.8 53 2>&1 && echo "✓ Public DNS reachable" || echo "✗ Public DNS not reachable"

if [ -n "$RDS_IP" ]; then
    echo "Testing direct IP connectivity to RDS:"
    timeout 5 nc -zv $RDS_IP $RDS_PORT 2>&1 && echo "✓ Direct IP connectivity works" || echo "✗ Direct IP connectivity failed"
fi

# Test Python imports before running main script
echo "=== TESTING PYTHON IMPORTS ==="
python3 -c "
try:
    import boto3
    print('✓ boto3 import successful')
    print('boto3 version:', boto3.__version__)
except ImportError as e:
    print('✗ boto3 import failed:', e)

try:
    import psycopg2
    print('✓ psycopg2 import successful')
except ImportError as e:
    print('✗ psycopg2 import failed:', e)
    
try:
    from dotenv import load_dotenv
    print('✓ python-dotenv import successful')
except ImportError as e:
    print('✗ python-dotenv import failed:', e)
"

# Run the discovery/import process based on operation mode
if [ "{operation_mode}" = "discovery" ]; then
    echo "Running in DISCOVERY mode..."
    python3 -c "
import sys
import os
import subprocess

# Set up the environment
sys.path.append('/parliament')
os.chdir('/parliament')

print('Starting Parliament data discovery...')

try:
    print('Running discovery service with real-time output...')
    # Use shell=True to avoid output buffering and show real-time progress
    result = subprocess.run(
        'python3 scripts/data_processing/discovery_service.py --discover-all 2>&1',
        shell=True, timeout={timeout_minutes * 60}
    )  # Use configured timeout: {timeout_minutes} minutes

    print('Discovery process completed with return code:', result.returncode)

except subprocess.TimeoutExpired:
    print('Discovery process timed out after {timeout_minutes} minutes')
except Exception as e:
    print(f'Discovery process failed: {{e}}')
"
elif [ "{operation_mode}" = "importer" ]; then
    echo "Running in IMPORTER mode..."
    python3 -c "
import sys
import os
import subprocess

# Set up the environment
sys.path.append('/parliament')
os.chdir('/parliament')

print('Starting Parliament data import...')

try:
    print('Running data importer with real-time output...')
    # Use shell=True to avoid output buffering and show real-time progress
    result = subprocess.run(
        'python3 scripts/data_processing/database_driven_importer.py 2>&1',
        shell=True, timeout={timeout_minutes * 60}
    )  # Use configured timeout: {timeout_minutes} minutes
    
    print('Import process completed with return code:', result.returncode)
    
except subprocess.TimeoutExpired:
    print('Import process timed out after {timeout_minutes} minutes')
except Exception as e:
    print(f'Import process failed: {{e}}')
"
else
    echo "Unknown operation mode: {operation_mode}. Defaulting to discovery."
    # Default to discovery if mode is not recognized
    python3 -c "
import sys
import os
import subprocess

# Set up the environment
sys.path.append('/parliament')
os.chdir('/parliament')

print('Starting Parliament data discovery (default)...')

try:
    print('Running discovery service with real-time output...')
    # Use shell=True to avoid output buffering and show real-time progress
    result = subprocess.run(
        'python3 scripts/data_processing/discovery_service.py --discover-all 2>&1',
        shell=True, timeout={timeout_minutes * 60}
    )  # Use configured timeout: {timeout_minutes} minutes

    print('Discovery process completed with return code:', result.returncode)

except subprocess.TimeoutExpired:
    print('Discovery process timed out after {timeout_minutes} minutes')
except Exception as e:
    print(f'Discovery process failed: {{e}}')
"
fi

# Signal completion 
echo "Parliament data import completed at $(date)"
echo "Instance will remain running for 5 minutes for debugging if needed"
echo "Use 'sudo shutdown -h now' to shutdown manually"

# Keep instance running for 5 minutes for debugging
echo "Waiting 5 minutes before automatic shutdown..."
sleep 300
echo "Auto-shutdown after 5 minute grace period"
shutdown -h now
"""
        
        # Encode user data
        user_data_encoded = base64.b64encode(user_data_script.encode()).decode()
        
        # Get subnet ID from environment (pick first public subnet to match RDS location)
        subnet_ids = os.environ.get('PUBLIC_SUBNET_IDS', '').split(',')
        subnet_id = subnet_ids[0] if subnet_ids and subnet_ids[0] else ''
        
        # Launch configuration (TagSpecifications not supported in spot requests)
        launch_config = {
            'ImageId': os.environ.get('AMI_ID', 'ami-0e9799f4d991f9aa0'),
            'InstanceType': instance_type,
            'UserData': user_data_encoded,
            'SecurityGroupIds': [os.environ.get('SECURITY_GROUP_ID', '')],
            'SubnetId': subnet_id,
            'IamInstanceProfile': {
                'Name': os.environ.get('IAM_INSTANCE_PROFILE', '')
            },
            'BlockDeviceMappings': [
                {
                    'DeviceName': '/dev/xvda',
                    'Ebs': {
                        'VolumeSize': 30,  # 30GB root volume (matches AMI snapshot size)
                        'VolumeType': 'gp3',
                        'DeleteOnTermination': True
                    }
                }
            ]
        }
        
        # Request spot instance
        response = ec2.request_spot_instances(
            SpotPrice='0.10',  # Max price for t3.large (~$0.05 current spot price)
            InstanceCount=1,
            LaunchSpecification=launch_config
        )
        
        spot_request_id = response['SpotInstanceRequests'][0]['SpotInstanceRequestId']
        
        # Tag the spot request (not the instance itself)
        try:
            ec2.create_tags(
                Resources=[spot_request_id],
                Tags=[
                    {'Key': 'Name', 'Value': 'parliament-data-import-request'},
                    {'Key': 'Project', 'Value': 'Parliament'},
                    {'Key': 'Purpose', 'Value': 'automated-data-import'},
                    {'Key': 'AutoTerminate', 'Value': 'true'}
                ]
            )
        except Exception as tag_error:
            logger.warning(f"Failed to tag spot request: {tag_error}")
        
        # Wait for the spot request to be fulfilled and get instance ID
        instance_id = None
        try:
            # Poll for up to 60 seconds to get the instance ID
            for attempt in range(12):  # 12 attempts * 5 seconds = 60 seconds
                time.sleep(5)
                spot_requests = ec2.describe_spot_instance_requests(
                    SpotInstanceRequestIds=[spot_request_id]
                )
                
                if spot_requests['SpotInstanceRequests']:
                    spot_request = spot_requests['SpotInstanceRequests'][0]
                    if spot_request['State'] == 'active' and 'InstanceId' in spot_request:
                        instance_id = spot_request['InstanceId']
                        logger.info(f"Spot instance launched: {instance_id}")
                        break
                    elif spot_request['State'] == 'failed':
                        logger.error(f"Spot request failed: {spot_request.get('Fault', {}).get('Message', 'Unknown error')}")
                        break
                        
        except Exception as poll_error:
            logger.warning(f"Failed to get instance ID: {poll_error}")
        
        logger.info(f"Spot instance requested: {spot_request_id}, Instance ID: {instance_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Spot instance launch initiated',
                'spotRequestId': spot_request_id,
                'instanceId': instance_id,
                'instanceType': instance_type,
                'timeoutMinutes': timeout_minutes,
                'automationMode': import_mode,
                'operationMode': operation_mode
            })
        }
        
    except Exception as e:
        logger.error(f"Error launching spot instance: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to launch spot instance',
                'message': str(e)
            })
        }