"""
CloudFlare DNS Updater Lambda Function

Automatically updates CloudFlare DNS records when ECS task public IP changes.
Triggered by ECS task state change events via EventBridge.

Cost: ~$0.01/month (triggered only on ECS restarts)
"""

import json
import os
import logging
import urllib.request
import urllib.error

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
CLOUDFLARE_API_TOKEN = os.environ.get('CLOUDFLARE_API_TOKEN', '')
CLOUDFLARE_ZONE_ID = os.environ.get('CLOUDFLARE_ZONE_ID', '')
DNS_RECORD_NAME = os.environ.get('DNS_RECORD_NAME', '')  # e.g., api.fiscaliza.pt
ECS_CLUSTER_NAME = os.environ.get('ECS_CLUSTER_NAME', '')
ECS_SERVICE_NAME = os.environ.get('ECS_SERVICE_NAME', '')


def get_cloudflare_record_id(zone_id: str, record_name: str) -> str | None:
    """Get the DNS record ID from CloudFlare."""
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?name={record_name}&type=A"

    req = urllib.request.Request(url, method='GET')
    req.add_header('Authorization', f'Bearer {CLOUDFLARE_API_TOKEN}')
    req.add_header('Content-Type', 'application/json')

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if data.get('success') and data.get('result'):
                return data['result'][0]['id']
    except urllib.error.HTTPError as e:
        logger.error(f"Failed to get DNS record: {e.code} - {e.read().decode()}")
    except Exception as e:
        logger.error(f"Error getting DNS record: {e}")

    return None


def update_cloudflare_dns(zone_id: str, record_id: str, record_name: str, ip_address: str) -> bool:
    """Update the DNS A record in CloudFlare."""
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"

    payload = json.dumps({
        'type': 'A',
        'name': record_name,
        'content': ip_address,
        'ttl': 60,  # 1 minute TTL for quick propagation
        'proxied': True  # Enable CloudFlare proxy for SSL termination
    }).encode('utf-8')

    req = urllib.request.Request(url, data=payload, method='PUT')
    req.add_header('Authorization', f'Bearer {CLOUDFLARE_API_TOKEN}')
    req.add_header('Content-Type', 'application/json')

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if data.get('success'):
                logger.info(f"Successfully updated DNS record {record_name} to {ip_address}")
                return True
            else:
                logger.error(f"CloudFlare API error: {data.get('errors')}")
    except urllib.error.HTTPError as e:
        logger.error(f"Failed to update DNS: {e.code} - {e.read().decode()}")
    except Exception as e:
        logger.error(f"Error updating DNS: {e}")

    return False


def create_cloudflare_dns(zone_id: str, record_name: str, ip_address: str) -> bool:
    """Create a new DNS A record in CloudFlare if it doesn't exist."""
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"

    payload = json.dumps({
        'type': 'A',
        'name': record_name,
        'content': ip_address,
        'ttl': 60,
        'proxied': True  # Enable CloudFlare proxy for SSL termination
    }).encode('utf-8')

    req = urllib.request.Request(url, data=payload, method='POST')
    req.add_header('Authorization', f'Bearer {CLOUDFLARE_API_TOKEN}')
    req.add_header('Content-Type', 'application/json')

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if data.get('success'):
                logger.info(f"Successfully created DNS record {record_name} pointing to {ip_address}")
                return True
            else:
                logger.error(f"CloudFlare API error: {data.get('errors')}")
    except urllib.error.HTTPError as e:
        logger.error(f"Failed to create DNS: {e.code} - {e.read().decode()}")
    except Exception as e:
        logger.error(f"Error creating DNS: {e}")

    return False


def get_ecs_task_public_ip(cluster: str, task_arn: str) -> str | None:
    """Get the public IP of an ECS task using boto3."""
    import boto3

    ecs = boto3.client('ecs')
    ec2 = boto3.client('ec2')

    try:
        # Describe the task to get ENI
        response = ecs.describe_tasks(cluster=cluster, tasks=[task_arn])

        if not response.get('tasks'):
            logger.warning(f"No task found for ARN: {task_arn}")
            return None

        task = response['tasks'][0]

        # Get the ENI attachment
        for attachment in task.get('attachments', []):
            if attachment.get('type') == 'ElasticNetworkInterface':
                for detail in attachment.get('details', []):
                    if detail.get('name') == 'networkInterfaceId':
                        eni_id = detail.get('value')

                        # Get the public IP from the ENI
                        eni_response = ec2.describe_network_interfaces(
                            NetworkInterfaceIds=[eni_id]
                        )

                        if eni_response.get('NetworkInterfaces'):
                            eni = eni_response['NetworkInterfaces'][0]
                            if 'Association' in eni:
                                return eni['Association'].get('PublicIp')

        logger.warning("No public IP found for task")
        return None

    except Exception as e:
        logger.error(f"Error getting task public IP: {e}")
        return None


def lambda_handler(event, context):
    """
    Handle ECS task state change events.

    Event structure:
    {
        "source": "aws.ecs",
        "detail-type": "ECS Task State Change",
        "detail": {
            "clusterArn": "arn:aws:ecs:...",
            "taskArn": "arn:aws:ecs:...",
            "lastStatus": "RUNNING",
            "desiredStatus": "RUNNING",
            ...
        }
    }
    """
    logger.info(f"Received event: {json.dumps(event)}")

    # Validate environment
    if not all([CLOUDFLARE_API_TOKEN, CLOUDFLARE_ZONE_ID, DNS_RECORD_NAME]):
        logger.error("Missing required environment variables")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Missing configuration'})
        }

    # Extract event details
    detail = event.get('detail', {})
    last_status = detail.get('lastStatus', '')
    desired_status = detail.get('desiredStatus', '')
    task_arn = detail.get('taskArn', '')
    cluster_arn = detail.get('clusterArn', '')

    # Extract cluster name from ARN
    cluster_name = cluster_arn.split('/')[-1] if cluster_arn else ''

    # Only process RUNNING tasks
    if last_status != 'RUNNING' or desired_status != 'RUNNING':
        logger.info(f"Ignoring task state: {last_status}/{desired_status}")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Task not in RUNNING state, skipping'})
        }

    # Filter by cluster/service if configured
    if ECS_CLUSTER_NAME and cluster_name != ECS_CLUSTER_NAME:
        logger.info(f"Ignoring cluster: {cluster_name}")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': f'Different cluster: {cluster_name}'})
        }

    # Get the task's public IP
    public_ip = get_ecs_task_public_ip(cluster_name, task_arn)

    if not public_ip:
        logger.warning("Could not determine task public IP")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Could not get public IP'})
        }

    logger.info(f"Task public IP: {public_ip}")

    # Update CloudFlare DNS
    record_id = get_cloudflare_record_id(CLOUDFLARE_ZONE_ID, DNS_RECORD_NAME)

    if record_id:
        success = update_cloudflare_dns(CLOUDFLARE_ZONE_ID, record_id, DNS_RECORD_NAME, public_ip)
    else:
        logger.info("DNS record not found, creating new record")
        success = create_cloudflare_dns(CLOUDFLARE_ZONE_ID, DNS_RECORD_NAME, public_ip)

    if success:
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'DNS updated successfully',
                'record': DNS_RECORD_NAME,
                'ip': public_ip
            })
        }
    else:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Failed to update DNS'})
        }
