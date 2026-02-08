#!/usr/bin/env python3
"""
Parliament Operations CLI

Unified command-line interface for deployment and orchestration operations.

Usage:
    ./ops.py deploy [infra|backend|frontend|all]
    ./ops.py pipeline [run|discover|import|status]
    ./ops.py logs [ecs|pipeline|lambda]
    ./ops.py database [clear|reset-imports|status|migrate|migration-status]

Examples:
    ./ops.py deploy all                    # Full stack deployment
    ./ops.py deploy backend                # Deploy backend only
    ./ops.py pipeline run -m discovery     # Run discovery on EC2 Spot
    ./ops.py pipeline run -m importer -w   # Run import and wait for completion
    ./ops.py logs ecs -f                   # Tail ECS logs
    ./ops.py logs pipeline -n 100          # View last 100 pipeline log lines
    ./ops.py database clear -y             # Clear all database tables
    ./ops.py database reset-imports        # Reset import status for re-import
    ./ops.py database migrate              # Run migrations on local database
    ./ops.py database migrate -p           # Run migrations on production database
    ./ops.py database migration-status -v  # Show migration history
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import click

from ops.config import get_config
from ops.deploy import deploy
from ops.pipeline import pipeline
from ops.logs import logs
from ops.database import database


@click.group()
@click.version_option(version="1.0.0", prog_name="Parliament Ops CLI")
def cli():
    """
    Parliament Operations CLI - Unified deployment and orchestration.

    \b
    Commands:
      deploy    Deploy infrastructure and applications
      pipeline  Remote pipeline orchestration
      logs      View logs from various sources
      database  Database management (clear, reset, status)

    \b
    Quick Start:
      ops.py deploy all           # Full deployment
      ops.py pipeline run         # Start data pipeline
      ops.py logs ecs -f          # Follow ECS logs
      ops.py database clear -y    # Clear database
    """
    pass


@cli.command()
def info():
    """Show current configuration and status."""
    config = get_config()

    click.echo(click.style("\n=== Parliament Ops Configuration ===", fg="cyan", bold=True))

    click.echo(f"\n  Project: {config.project_name}")
    click.echo(f"  Environment: {config.environment}")
    click.echo(f"  Domain: {config.domain_name}")

    click.echo(click.style("\n  AWS:", bold=True))
    click.echo(f"    Region: {config.aws.region}")
    click.echo(f"    Account: {config.aws.account_id or 'Not configured'}")
    click.echo(f"    Profile: {config.aws.profile or 'default'}")

    click.echo(click.style("\n  ECS:", bold=True))
    click.echo(f"    Cluster: {config.ecs.cluster_name}")
    click.echo(f"    Service: {config.ecs.service_name}")

    click.echo(click.style("\n  ECR:", bold=True))
    click.echo(f"    Repository: {config.ecr.repository_url or 'Not configured'}")

    click.echo(click.style("\n  S3/CloudFront:", bold=True))
    click.echo(f"    Bucket: {config.s3.bucket_name or 'Not configured'}")
    click.echo(f"    Distribution: {config.s3.cloudfront_distribution_id or 'Not configured'}")

    click.echo(click.style("\n  Pipeline:", bold=True))
    click.echo(f"    Lambda URL: {config.pipeline.lambda_function_url or 'Not configured'}")
    click.echo(f"    Spot Instance: {config.pipeline.spot_instance_type}")
    click.echo(f"    Timeout: {config.pipeline.timeout_minutes} minutes")

    click.echo(click.style("\n  Paths:", bold=True))
    click.echo(f"    Project Root: {config.project_root}")
    click.echo(f"    Terraform: {config.terraform_dir}")
    click.echo(f"    Frontend: {config.frontend_dir}")


# Register command groups
cli.add_command(deploy)
cli.add_command(pipeline)
cli.add_command(logs)
cli.add_command(database)


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
