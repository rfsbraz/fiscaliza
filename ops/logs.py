"""
Log viewing commands for Parliament Operations CLI.

View logs from ECS, CloudWatch, and pipeline executions.
"""

import json
from datetime import datetime, timedelta
from typing import Optional

import click

try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

from .config import get_config, Config


def get_log_events(
    log_group: str,
    region: str,
    stream_prefix: Optional[str] = None,
    limit: int = 100,
    since_minutes: int = 60,
    profile: Optional[str] = None
) -> list:
    """Get log events from CloudWatch."""
    if not HAS_BOTO3:
        raise click.ClickException("boto3 not installed. Run: pip install boto3")

    session = boto3.Session(profile_name=profile, region_name=region) if profile else boto3.Session(region_name=region)
    logs = session.client('logs')

    try:
        # Find log streams
        kwargs = {
            'logGroupName': log_group,
            'orderBy': 'LastEventTime',
            'descending': True,
            'limit': 10
        }
        if stream_prefix:
            kwargs['logStreamNamePrefix'] = stream_prefix

        streams_response = logs.describe_log_streams(**kwargs)

        if not streams_response.get('logStreams'):
            return []

        # Calculate start time
        start_time = int((datetime.now() - timedelta(minutes=since_minutes)).timestamp() * 1000)

        all_events = []

        # Get events from recent streams
        for stream in streams_response['logStreams'][:3]:
            stream_name = stream['logStreamName']

            try:
                events_response = logs.get_log_events(
                    logGroupName=log_group,
                    logStreamName=stream_name,
                    startTime=start_time,
                    limit=limit,
                    startFromHead=False
                )

                for event in events_response.get('events', []):
                    all_events.append({
                        'timestamp': datetime.fromtimestamp(event['timestamp'] / 1000),
                        'message': event['message'].strip(),
                        'stream': stream_name
                    })
            except Exception:
                continue

        # Sort by timestamp
        all_events.sort(key=lambda x: x['timestamp'])

        return all_events[-limit:]

    except logs.exceptions.ResourceNotFoundException:
        return []
    except Exception as e:
        click.echo(click.style(f"  Warning: Could not fetch logs: {e}", fg="yellow"))
        return []


def tail_logs(log_group: str, region: str, stream_prefix: Optional[str] = None, profile: Optional[str] = None):
    """Tail logs in real-time."""
    import time

    if not HAS_BOTO3:
        raise click.ClickException("boto3 not installed")

    session = boto3.Session(profile_name=profile, region_name=region) if profile else boto3.Session(region_name=region)
    logs_client = session.client('logs')
    last_timestamp = int((datetime.now() - timedelta(minutes=5)).timestamp() * 1000)
    seen_event_ids = set()

    click.echo(click.style(f"Tailing {log_group}... (Ctrl+C to stop)", fg="cyan"))

    try:
        while True:
            try:
                # Find recent streams
                kwargs = {
                    'logGroupName': log_group,
                    'orderBy': 'LastEventTime',
                    'descending': True,
                    'limit': 3
                }
                if stream_prefix:
                    kwargs['logStreamNamePrefix'] = stream_prefix

                streams = logs_client.describe_log_streams(**kwargs)

                for stream in streams.get('logStreams', []):
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
                                click.echo(f"[{ts.strftime('%H:%M:%S')}] {msg}")
                                last_timestamp = max(last_timestamp, event['timestamp'] + 1)

                    except Exception:
                        continue

            except Exception as e:
                click.echo(click.style(f"Error: {e}", fg="red"))

            time.sleep(2)

    except KeyboardInterrupt:
        click.echo("\nStopped tailing.")


@click.group()
def logs():
    """View logs from various sources."""
    pass


@logs.command()
@click.option('--lines', '-n', default=50, help='Number of lines to show')
@click.option('--since', '-s', default=60, help='Show logs from last N minutes')
@click.option('--follow', '-f', is_flag=True, help='Follow log output (tail -f)')
@click.option('--production', '-p', is_flag=True, default=True, help='View production logs (default)')
@click.option('--local', '-l', is_flag=True, help='View local logs')
def ecs(lines: int, since: int, follow: bool, production: bool, local: bool):
    """View ECS container logs."""
    config = get_config()

    if local:
        click.echo(click.style("\n=== ECS Logs (Local) ===", fg="cyan", bold=True))
        click.echo("  Local ECS logs not available. Use docker logs or check container output.")
        return

    log_group = f"/ecs/fiscaliza-{config.environment}/backend"

    click.echo(click.style(f"\n=== ECS Logs ({log_group}) ===", fg="cyan", bold=True))

    if follow:
        tail_logs(log_group, config.aws.region, profile=config.aws.profile)
    else:
        events = get_log_events(log_group, config.aws.region, limit=lines, since_minutes=since, profile=config.aws.profile)

        if not events:
            click.echo("  No log events found.")
            return

        for event in events:
            ts = event['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            msg = event['message']

            # Color code by log level
            if 'ERROR' in msg or 'Error' in msg:
                click.echo(click.style(f"[{ts}] {msg}", fg="red"))
            elif 'WARNING' in msg or 'Warning' in msg:
                click.echo(click.style(f"[{ts}] {msg}", fg="yellow"))
            else:
                click.echo(f"[{ts}] {msg}")


@logs.command(name='pipeline')
@click.option('--lines', '-n', default=100, help='Number of lines to show')
@click.option('--since', '-s', default=120, help='Show logs from last N minutes')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.option('--production', '-p', is_flag=True, default=True, help='View production logs (default)')
@click.option('--local', '-l', is_flag=True, help='View local logs')
def pipeline_logs(lines: int, since: int, follow: bool, production: bool, local: bool):
    """View pipeline execution logs."""
    config = get_config()

    if local:
        click.echo(click.style("\n=== Pipeline Logs (Local) ===", fg="cyan", bold=True))
        click.echo("  Local pipeline logs: Check console output or log files in project directory.")
        return

    log_group = "/aws/parliament/import"

    click.echo(click.style(f"\n=== Pipeline Logs ({log_group}) ===", fg="cyan", bold=True))

    if follow:
        tail_logs(log_group, config.aws.region, profile=config.aws.profile)
    else:
        events = get_log_events(log_group, config.aws.region, limit=lines, since_minutes=since, profile=config.aws.profile)

        if not events:
            click.echo("  No log events found.")
            click.echo("  (Pipeline logs appear after a pipeline run is started)")
            return

        for event in events:
            ts = event['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            msg = event['message']

            # Sanitize Unicode characters for Windows console compatibility
            msg = msg.replace('\u2713', '[OK]').replace('\u2717', '[X]').replace('\u2714', '[OK]').replace('\u2716', '[X]')

            # Highlight important messages
            if 'ERROR' in msg or 'Failed' in msg or 'failed' in msg:
                click.echo(click.style(f"[{ts}] {msg}", fg="red"))
            elif 'SUCCESS' in msg or 'completed' in msg or 'Completed' in msg:
                click.echo(click.style(f"[{ts}] {msg}", fg="green"))
            elif 'Starting' in msg or 'STARTING' in msg:
                click.echo(click.style(f"[{ts}] {msg}", fg="cyan"))
            elif 'Warning' in msg or 'WARNING' in msg:
                click.echo(click.style(f"[{ts}] {msg}", fg="yellow"))
            else:
                click.echo(f"[{ts}] {msg}")


@logs.command()
@click.option('--lines', '-n', default=50, help='Number of lines to show')
@click.option('--since', '-s', default=60, help='Show logs from last N minutes')
@click.option('--production', '-p', is_flag=True, default=True, help='View production logs (default)')
def lambda_logs(lines: int, since: int, production: bool):
    """View Lambda function logs (spot-launcher)."""
    config = get_config()
    function_name = f"fiscaliza-{config.environment}-spot-launcher"
    log_group = f"/aws/lambda/{function_name}"

    click.echo(click.style(f"\n=== Lambda Logs ({function_name}) ===", fg="cyan", bold=True))

    events = get_log_events(log_group, config.aws.region, limit=lines, since_minutes=since, profile=config.aws.profile)

    if not events:
        click.echo("  No log events found.")
        return

    for event in events:
        ts = event['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        msg = event['message']

        # Skip START/END/REPORT messages for cleaner output
        if msg.startswith('START ') or msg.startswith('END ') or msg.startswith('REPORT '):
            continue

        if 'ERROR' in msg or 'Error' in msg:
            click.echo(click.style(f"[{ts}] {msg}", fg="red"))
        else:
            click.echo(f"[{ts}] {msg}")
