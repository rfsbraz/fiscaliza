"""
Pipeline orchestration commands for Parliament Operations CLI.

Unified entry point for both local and remote (ECS) pipeline execution.

Usage:
    ops pipeline run --local       # Rich UI local execution
    ops pipeline run --ecs         # ECS Fargate execution
    ops pipeline status            # Show import status
    ops pipeline logs              # Tail ECS logs
"""

import asyncio
import json
import sys
import time
from datetime import datetime, timedelta
from typing import Optional

import click

try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

try:
    import urllib.request
    import urllib.error
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False

from .config import get_config, Config


def get_boto3_session(config: Config):
    """Get boto3 session with proper credentials."""
    if not HAS_BOTO3:
        raise click.ClickException("boto3 not installed. Run: pip install boto3")

    if config.aws.profile:
        return boto3.Session(profile_name=config.aws.profile, region_name=config.aws.region)
    return boto3.Session(region_name=config.aws.region)


def get_terraform_output(terraform_dir, output_name: str) -> str:
    """Get a specific terraform output value."""
    import subprocess
    try:
        result = subprocess.run(
            ["terraform", "output", "-raw", output_name],
            cwd=terraform_dir,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def run_ecs_task(config: Config, task_type: str) -> dict:
    """Run an ECS task for import pipeline."""
    session = get_boto3_session(config)
    ecs = session.client('ecs')

    # Get task definition ARN from terraform outputs
    if task_type == 'discovery':
        task_arn = get_terraform_output(config.terraform_dir, "ecs_import_discovery_task_arn")
    else:
        task_arn = get_terraform_output(config.terraform_dir, "ecs_import_importer_task_arn")

    if not task_arn:
        raise click.ClickException(f"Could not get ECS task ARN for {task_type}. Run 'terraform apply' first.")

    # Get network configuration
    public_subnets = get_terraform_output(config.terraform_dir, "public_subnet_ids")
    security_group = get_terraform_output(config.terraform_dir, "ecs_import_security_group_id")
    cluster_name = get_terraform_output(config.terraform_dir, "ecs_cluster_name")

    if not all([public_subnets, security_group, cluster_name]):
        raise click.ClickException("Could not get network configuration from terraform outputs")

    # Parse subnet IDs (terraform outputs them as JSON array)
    try:
        if public_subnets.startswith('['):
            subnet_ids = json.loads(public_subnets)
        else:
            subnet_ids = [s.strip() for s in public_subnets.split(',')]
    except Exception:
        subnet_ids = [public_subnets]

    # Run the task
    response = ecs.run_task(
        cluster=cluster_name,
        taskDefinition=task_arn,
        launchType='FARGATE',
        count=1,
        networkConfiguration={
            'awsvpcConfiguration': {
                'subnets': subnet_ids,
                'securityGroups': [security_group],
                'assignPublicIp': 'ENABLED'
            }
        },
        startedBy='ops-cli'
    )

    if response.get('failures'):
        failure = response['failures'][0]
        raise click.ClickException(f"Failed to start task: {failure.get('reason', 'Unknown error')}")

    task = response['tasks'][0]
    return {
        'task_arn': task['taskArn'],
        'task_id': task['taskArn'].split('/')[-1],
        'cluster': cluster_name,
        'status': task['lastStatus'],
        'created_at': str(task.get('createdAt', '')),
    }


def get_ecs_task_status(config: Config, task_id: str) -> dict:
    """Get status of an ECS task."""
    session = get_boto3_session(config)
    ecs = session.client('ecs')

    cluster_name = get_terraform_output(config.terraform_dir, "ecs_cluster_name")

    try:
        response = ecs.describe_tasks(
            cluster=cluster_name,
            tasks=[task_id]
        )

        if not response.get('tasks'):
            return {'status': 'NOT_FOUND'}

        task = response['tasks'][0]

        # Get exit code if available
        exit_code = None
        if task.get('containers'):
            container = task['containers'][0]
            exit_code = container.get('exitCode')

        return {
            'status': task['lastStatus'],
            'desired_status': task.get('desiredStatus', ''),
            'exit_code': exit_code,
            'stopped_reason': task.get('stoppedReason', ''),
            'created_at': str(task.get('createdAt', '')),
            'started_at': str(task.get('startedAt', '')),
            'stopped_at': str(task.get('stoppedAt', '')),
        }
    except Exception as e:
        return {'status': 'ERROR', 'error': str(e)}


def list_ecs_import_tasks(config: Config, status_filter: str = None) -> list:
    """List recent ECS import tasks."""
    session = get_boto3_session(config)
    ecs = session.client('ecs')

    cluster_name = get_terraform_output(config.terraform_dir, "ecs_cluster_name")

    tasks = []

    # Get running tasks
    try:
        running = ecs.list_tasks(
            cluster=cluster_name,
            desiredStatus='RUNNING',
            startedBy='ops-cli'
        )
        tasks.extend(running.get('taskArns', []))
    except Exception:
        pass

    # Get stopped tasks (recent)
    try:
        stopped = ecs.list_tasks(
            cluster=cluster_name,
            desiredStatus='STOPPED',
            startedBy='ops-cli'
        )
        tasks.extend(stopped.get('taskArns', []))
    except Exception:
        pass

    if not tasks:
        return []

    # Get task details
    try:
        response = ecs.describe_tasks(cluster=cluster_name, tasks=tasks[:10])
        return response.get('tasks', [])
    except Exception:
        return []


def tail_ecs_logs(config: Config, task_type: str = 'discovery', follow: bool = True):
    """Tail logs from ECS import tasks."""
    session = get_boto3_session(config)
    logs_client = session.client('logs')

    log_group = f"/ecs/fiscaliza-{config.environment}/import"
    stream_prefix = task_type  # 'discovery' or 'importer'

    last_timestamp = int((datetime.now() - timedelta(minutes=30)).timestamp() * 1000)
    seen_event_ids = set()

    click.echo(click.style(f"Tailing {log_group}/{stream_prefix}... (Ctrl+C to stop)", fg="cyan"))

    try:
        while True:
            try:
                # Find recent streams
                streams_response = logs_client.describe_log_streams(
                    logGroupName=log_group,
                    logStreamNamePrefix=stream_prefix,
                    orderBy='LastEventTime',
                    descending=True,
                    limit=3
                )

                for stream in streams_response.get('logStreams', []):
                    stream_name = stream['logStreamName']

                    try:
                        events = logs_client.get_log_events(
                            logGroupName=log_group,
                            logStreamName=stream_name,
                            startTime=last_timestamp,
                            startFromHead=False
                        )

                        for event in events.get('events', []):
                            event_id = f"{event['timestamp']}-{hash(event['message'])}"
                            if event_id not in seen_event_ids:
                                seen_event_ids.add(event_id)
                                ts = datetime.fromtimestamp(event['timestamp'] / 1000)
                                msg = event['message'].strip()

                                # Sanitize Unicode for Windows
                                msg = msg.replace('\u2713', '[OK]').replace('\u2717', '[X]')
                                msg = msg.replace('\u2714', '[OK]').replace('\u2716', '[X]')

                                # Color code by content
                                if 'ERROR' in msg or 'Error' in msg or 'failed' in msg.lower():
                                    click.echo(click.style(f"[{ts.strftime('%H:%M:%S')}] {msg}", fg="red"))
                                elif 'SUCCESS' in msg or 'completed' in msg.lower():
                                    click.echo(click.style(f"[{ts.strftime('%H:%M:%S')}] {msg}", fg="green"))
                                elif 'WARNING' in msg or 'Warning' in msg:
                                    click.echo(click.style(f"[{ts.strftime('%H:%M:%S')}] {msg}", fg="yellow"))
                                else:
                                    click.echo(f"[{ts.strftime('%H:%M:%S')}] {msg}")

                                last_timestamp = max(last_timestamp, event['timestamp'] + 1)

                    except Exception:
                        continue

                if not follow:
                    break

            except logs_client.exceptions.ResourceNotFoundException:
                click.echo(click.style("  Log group not found. Run an import task first.", fg="yellow"))
                break
            except Exception as e:
                click.echo(click.style(f"Error: {e}", fg="red"))

            if follow:
                time.sleep(2)

    except KeyboardInterrupt:
        click.echo("\nStopped tailing.")


def get_import_status(config: Config) -> dict:
    """Get import status from the API."""
    api_url = f"https://api.{config.domain_name}/api/admin/import-stats"

    try:
        req = urllib.request.Request(api_url, method='GET')
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception:
        try:
            req = urllib.request.Request("http://localhost:5000/api/admin/import-stats", method='GET')
            with urllib.request.urlopen(req, timeout=5) as response:
                return json.loads(response.read().decode())
        except Exception:
            return {}


@click.group()
def pipeline():
    """Pipeline orchestration - unified local and ECS execution.

    Run data import pipelines locally (default) or on ECS Fargate.
    Local mode provides a Rich terminal UI with real-time progress.

    Examples:
        ops pipeline run                  # Full pipeline, local with Rich UI
        ops pipeline run -d prod          # Local against production database
        ops pipeline run --ecs            # Run on ECS Fargate
        ops pipeline discover             # Discovery only
        ops pipeline status               # Check status
    """
    pass


@pipeline.command()
@click.option('--mode', '-m', type=click.Choice(['discovery', 'importer', 'full']), default='full',
              help='Pipeline mode: discovery, importer, or full (default: full)')
@click.option('--wait', '-w', is_flag=True, help='Wait for ECS completion and show logs')
@click.option('--local', '-l', is_flag=True, default=True, help='Run locally with Rich UI (default)')
@click.option('--ecs', '-e', is_flag=True, help='Run on ECS Fargate instead of locally')
@click.option('--database', '-d', type=click.Choice(['local', 'prod', 'auto']), default='auto',
              help='Database: local, prod, or auto-detect (default: auto)')
@click.option('--max-downloads', type=int, default=5, help='Max concurrent downloads (local mode)')
@click.option('--file-types', type=str, default='XML', help='File types to process (comma-separated)')
@click.option('--stop-on-error', is_flag=True, help='Stop pipeline on first error (local mode)')
@click.option('--download-only', is_flag=True, help='Only download, skip import (local mode)')
@click.option('--import-only', is_flag=True, help='Only import, skip download (local mode)')
@click.option('--retry-failed', is_flag=True, help='Reset failed imports to pending before starting')
def run(mode: str, wait: bool, local: bool, ecs: bool, database: str,
        max_downloads: int, file_types: str,
        stop_on_error: bool, download_only: bool, import_only: bool, retry_failed: bool):
    """Start import pipeline locally (default) or on ECS Fargate.

    By default, runs locally with a Rich terminal UI showing real-time progress.
    Use --ecs flag to run on ECS Fargate instead.

    Examples:
        ops pipeline run                    # Local with Rich UI
        ops pipeline run --database prod    # Local against production DB
        ops pipeline run --ecs              # Run on ECS Fargate
        ops pipeline run --ecs -m discovery # Run only discovery on ECS
    """
    config = get_config()

    # --ecs flag overrides --local
    if ecs:
        local = False

    # Handle local mode with Rich UI
    if local:
        click.echo(click.style(f"\n=== Starting Pipeline - LOCAL (Rich UI) ===", fg="cyan", bold=True))

        try:
            from scripts.data_processing.pipeline_runner import (
                setup_database_environment,
                LocalPipelineRunner
            )
        except ImportError as e:
            raise click.ClickException(
                f"Failed to import pipeline runner: {e}\n"
                "Make sure you're running from the project root."
            )

        # Setup database
        try:
            db_config = setup_database_environment(database)
            click.echo(f"  Database: {db_config.display_name}")
        except RuntimeError as e:
            raise click.ClickException(str(e))

        # Handle retry-failed
        if retry_failed:
            try:
                from database.connection import DatabaseSession
                from database.models import ImportStatus
                from sqlalchemy import update

                with DatabaseSession() as db_session:
                    result = db_session.execute(
                        update(ImportStatus)
                        .where(ImportStatus.status == 'import_error')
                        .values(status='pending', error_message=None)
                    )
                    db_session.commit()
                    click.echo(f"  Reset {result.rowcount} failed imports")
            except Exception as e:
                click.echo(click.style(f"  Warning: Could not reset failed imports: {e}", fg="yellow"))

        # Parse file types
        allowed_file_types = [ft.strip() for ft in file_types.split(',')] if file_types else ['XML']

        # Determine mode flags
        if mode == 'discovery':
            download_only = True
            import_only = False
        elif mode == 'importer':
            download_only = False
            import_only = True

        # Create and run the pipeline
        # NOTE: max_concurrent_imports=1 is hardcoded to prevent deadlocks
        # on partidos/deputados tables during concurrent upserts
        runner = LocalPipelineRunner(
            db_config=db_config,
            max_concurrent_downloads=max_downloads,
            max_concurrent_imports=1,
            allowed_file_types=allowed_file_types,
            stop_on_error=stop_on_error,
            download_only=download_only,
            import_only=import_only
        )

        try:
            asyncio.run(runner.run())
        except KeyboardInterrupt:
            click.echo("\n  Pipeline interrupted.")
        except Exception as e:
            raise click.ClickException(f"Pipeline failed: {e}")

        return

    # ECS mode (production)
    click.echo(click.style(f"\n=== Starting Pipeline ({mode}) - ECS ===", fg="cyan", bold=True))
    click.echo(f"  Region: {config.aws.region}")

    if mode == 'full':
        # Run discovery first, then importer
        click.echo("\n  Running full pipeline: discovery then importer...")

        # Start discovery
        click.echo("\n  Starting discovery task...")
        discovery_result = run_ecs_task(config, 'discovery')
        click.echo(click.style(f"  Discovery task started: {discovery_result['task_id']}", fg="green"))

        if wait:
            click.echo("  Waiting for discovery to complete...")
            while True:
                time.sleep(10)
                status = get_ecs_task_status(config, discovery_result['task_id'])
                if status['status'] == 'STOPPED':
                    if status.get('exit_code') == 0:
                        click.echo(click.style("  Discovery completed successfully!", fg="green"))
                        break
                    else:
                        click.echo(click.style(f"  Discovery failed: {status.get('stopped_reason', 'Unknown')}", fg="red"))
                        return
                elif status['status'] == 'RUNNING':
                    click.echo(f"    [{datetime.now().strftime('%H:%M:%S')}] Discovery running...")
                else:
                    click.echo(f"    [{datetime.now().strftime('%H:%M:%S')}] Status: {status['status']}")

            # Now run importer
            click.echo("\n  Starting importer task...")
            importer_result = run_ecs_task(config, 'importer')
            click.echo(click.style(f"  Importer task started: {importer_result['task_id']}", fg="green"))

            click.echo("  Waiting for importer to complete...")
            while True:
                time.sleep(10)
                status = get_ecs_task_status(config, importer_result['task_id'])
                if status['status'] == 'STOPPED':
                    if status.get('exit_code') == 0:
                        click.echo(click.style("  Importer completed successfully!", fg="green"))
                    else:
                        click.echo(click.style(f"  Importer failed: {status.get('stopped_reason', 'Unknown')}", fg="red"))
                    break
                elif status['status'] == 'RUNNING':
                    click.echo(f"    [{datetime.now().strftime('%H:%M:%S')}] Importer running...")
        else:
            click.echo("\n  Tip: Use --wait to wait for completion, or monitor with:")
            click.echo(f"    ops pipeline logs -m discovery")
    else:
        # Single mode
        result = run_ecs_task(config, mode)
        click.echo(click.style(f"\n  Task started successfully!", fg="green"))
        click.echo(f"  Task ID: {result['task_id']}")
        click.echo(f"  Cluster: {result['cluster']}")
        click.echo(f"  Status: {result['status']}")

        if wait:
            click.echo("\n  Waiting for completion (Ctrl+C to stop watching)...")
            try:
                while True:
                    time.sleep(10)
                    status = get_ecs_task_status(config, result['task_id'])

                    if status['status'] == 'STOPPED':
                        if status.get('exit_code') == 0:
                            click.echo(click.style(f"\n  Task completed successfully!", fg="green"))
                        else:
                            click.echo(click.style(f"\n  Task failed: {status.get('stopped_reason', 'Unknown')}", fg="red"))
                            click.echo(f"  Exit code: {status.get('exit_code')}")
                        break
                    elif status['status'] == 'RUNNING':
                        click.echo(f"    [{datetime.now().strftime('%H:%M:%S')}] Task running...")
                    else:
                        click.echo(f"    [{datetime.now().strftime('%H:%M:%S')}] Status: {status['status']}")
            except KeyboardInterrupt:
                click.echo("\n  Stopped watching. Task continues in background.")
        else:
            click.echo(f"\n  View logs: ops pipeline logs -m {mode}")
            click.echo(f"  Check status: ops pipeline status")


@pipeline.command()
@click.option('--wait', '-w', is_flag=True, help='Wait for ECS completion')
@click.option('--ecs', '-e', is_flag=True, help='Run on ECS Fargate instead of locally')
@click.option('--database', '-d', type=click.Choice(['local', 'prod', 'auto']), default='auto',
              help='Database: local, prod, or auto-detect')
def discover(wait: bool, ecs: bool, database: str):
    """Run discovery only (find new files on parliament.pt)."""
    ctx = click.get_current_context()
    ctx.invoke(run, mode='discovery', wait=wait, ecs=ecs, database=database, download_only=True)


@pipeline.command(name='import')
@click.option('--wait', '-w', is_flag=True, help='Wait for ECS completion')
@click.option('--ecs', '-e', is_flag=True, help='Run on ECS Fargate instead of locally')
@click.option('--database', '-d', type=click.Choice(['local', 'prod', 'auto']), default='auto',
              help='Database: local, prod, or auto-detect')
@click.option('--retry-failed', is_flag=True, help='Reset failed imports to pending')
def import_cmd(wait: bool, ecs: bool, database: str, retry_failed: bool):
    """Run import only (process downloaded files)."""
    ctx = click.get_current_context()
    ctx.invoke(run, mode='importer', wait=wait, ecs=ecs, database=database, import_only=True, retry_failed=retry_failed)


@pipeline.command()
@click.option('--mode', '-m', type=click.Choice(['discovery', 'importer']), default='discovery',
              help='Which task logs to show')
@click.option('--follow', '-f', is_flag=True, help='Follow log output in real-time')
@click.option('--lines', '-n', type=int, default=50, help='Number of lines to show')
def logs(mode: str, follow: bool, lines: int):
    """View import task logs."""
    config = get_config()

    click.echo(click.style(f"\n=== Import Logs ({mode}) ===", fg="cyan", bold=True))

    if follow:
        tail_ecs_logs(config, task_type=mode, follow=True)
    else:
        tail_ecs_logs(config, task_type=mode, follow=False)


@pipeline.command()
def status():
    """Check pipeline and import task status."""
    config = get_config()

    click.echo(click.style("\n=== Pipeline Status ===", fg="cyan", bold=True))

    # Check for running/recent ECS tasks
    click.echo("\n  Recent Import Tasks:")
    tasks = list_ecs_import_tasks(config)

    if tasks:
        for task in tasks[:5]:
            task_id = task['taskArn'].split('/')[-1]
            status = task['lastStatus']

            # Get task family (discovery or importer)
            task_def = task.get('taskDefinitionArn', '')
            task_type = 'discovery' if 'discovery' in task_def else 'importer'

            # Format time
            created = task.get('createdAt')
            if created:
                created_str = created.strftime('%Y-%m-%d %H:%M:%S') if hasattr(created, 'strftime') else str(created)[:19]
            else:
                created_str = 'Unknown'

            # Color by status
            if status == 'RUNNING':
                status_str = click.style(status, fg='cyan')
            elif status == 'STOPPED':
                exit_code = None
                if task.get('containers'):
                    exit_code = task['containers'][0].get('exitCode')
                if exit_code == 0:
                    status_str = click.style('COMPLETED', fg='green')
                else:
                    status_str = click.style(f'FAILED (exit {exit_code})', fg='red')
            else:
                status_str = click.style(status, fg='yellow')

            click.echo(f"    {task_id[:12]}... [{task_type}] {status_str} - {created_str}")
    else:
        click.echo("    No recent import tasks found.")
        click.echo("    Run 'ops pipeline run -m discovery' to start a new import.")

    # Get import statistics from API
    click.echo("\n  Import Statistics:")
    stats = get_import_status(config)

    if stats:
        click.echo(f"    Total files: {stats.get('total', 'N/A')}")
        click.echo(f"    Completed: {stats.get('completed', 'N/A')}")
        click.echo(f"    Pending: {stats.get('pending', 'N/A')}")
        click.echo(f"    Failed: {stats.get('failed', 'N/A')}")
        if stats.get('total_records'):
            click.echo(f"    Records imported: {stats.get('total_records', 'N/A')}")
    else:
        click.echo("    Could not fetch import statistics (API not reachable)")

    # Show schedule status
    click.echo("\n  Scheduled Imports:")
    click.echo("    Discovery: Daily at 2 AM UTC")
    click.echo("    Importer:  Daily at 4 AM UTC")
    click.echo("    (Enable with: terraform apply -var='enable_scheduled_import=true')")
