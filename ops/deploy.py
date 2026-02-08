"""
Deployment commands for Parliament Operations CLI.

Handles infrastructure, backend, and frontend deployments.
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from .config import get_config, Config


def run_command(cmd: list[str], cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command with real-time output."""
    click.echo(f"  $ {' '.join(cmd)}")
    # On Windows, use shell=True for commands like npm, aws, docker
    use_shell = sys.platform == 'win32'
    result = subprocess.run(
        cmd,
        cwd=cwd,
        check=False,
        shell=use_shell
    )
    if check and result.returncode != 0:
        raise click.ClickException(f"Command failed with exit code {result.returncode}")
    return result


def deploy_infrastructure(config: Config, auto_approve: bool = False) -> bool:
    """Deploy Terraform infrastructure."""
    click.echo(click.style("\n[Infrastructure] Deploying with Terraform...", fg="blue", bold=True))

    terraform_dir = config.terraform_dir

    # Initialize
    click.echo("  Initializing Terraform...")
    run_command(["terraform", "init"], cwd=terraform_dir)

    # Plan
    click.echo("  Creating execution plan...")
    run_command(["terraform", "plan", "-out=tfplan"], cwd=terraform_dir)

    # Apply
    if auto_approve:
        click.echo("  Applying changes (auto-approved)...")
        run_command(["terraform", "apply", "tfplan"], cwd=terraform_dir)
    else:
        if click.confirm("  Apply infrastructure changes?", default=False):
            run_command(["terraform", "apply", "tfplan"], cwd=terraform_dir)
        else:
            click.echo("  Skipped infrastructure deployment.")
            return False

    click.echo(click.style("  Infrastructure deployed successfully!", fg="green"))
    return True


def check_aws_credentials(profile: Optional[str] = None) -> bool:
    """Check if AWS credentials are configured."""
    cmd = ["aws", "sts", "get-caller-identity"]
    if profile:
        cmd.extend(["--profile", profile])
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )
    return result.returncode == 0


def deploy_backend(config: Config) -> bool:
    """Build and deploy backend to ECS."""
    click.echo(click.style("\n[Backend] Building and deploying to ECS...", fg="blue", bold=True))

    project_root = config.project_root
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    # Check if ECR repository URL is available
    if not config.ecr.repository_url:
        raise click.ClickException("ECR repository URL not configured. Run 'ops deploy infra' first.")

    # Check AWS credentials
    click.echo("  Checking AWS credentials...")
    if config.aws.profile:
        click.echo(f"  Using AWS profile: {config.aws.profile}")

    if not check_aws_credentials(config.aws.profile):
        click.echo(click.style("\n  AWS credentials not configured!", fg="red", bold=True))
        click.echo("\n  Please configure credentials using one of these methods:")
        click.echo("    1. Run: aws configure")
        click.echo("    2. Set environment variables:")
        click.echo("       set AWS_ACCESS_KEY_ID=your-key")
        click.echo("       set AWS_SECRET_ACCESS_KEY=your-secret")
        click.echo("    3. If using AWS SSO: aws sso login")
        raise click.ClickException("AWS credentials required for deployment.")

    # Build AWS CLI command with profile if set
    def aws_cmd(base_cmd: list) -> list:
        if config.aws.profile:
            return base_cmd + ["--profile", config.aws.profile]
        return base_cmd

    # Login to ECR
    click.echo("  Logging into Amazon ECR...")
    login_cmd = subprocess.run(
        aws_cmd(["aws", "ecr", "get-login-password", "--region", config.aws.region]),
        capture_output=True,
        text=True,
        check=True
    )
    docker_login = subprocess.run(
        ["docker", "login", "--username", "AWS", "--password-stdin",
         f"{config.aws.account_id}.dkr.ecr.{config.aws.region}.amazonaws.com"],
        input=login_cmd.stdout,
        capture_output=True,
        text=True
    )
    if docker_login.returncode != 0:
        raise click.ClickException(f"Docker login failed: {docker_login.stderr}")

    # Build Docker image
    click.echo("  Building Docker image...")
    run_command(
        ["docker", "build", "-t", f"{config.project_name}-backend", "."],
        cwd=project_root
    )

    # Tag images
    click.echo("  Tagging images...")
    run_command([
        "docker", "tag",
        f"{config.project_name}-backend:latest",
        f"{config.ecr.repository_url}:latest"
    ])
    run_command([
        "docker", "tag",
        f"{config.project_name}-backend:latest",
        f"{config.ecr.repository_url}:{timestamp}"
    ])

    # Push images
    click.echo("  Pushing images to ECR...")
    run_command(["docker", "push", f"{config.ecr.repository_url}:latest"])
    run_command(["docker", "push", f"{config.ecr.repository_url}:{timestamp}"])

    # Update ECS service
    click.echo("  Updating ECS service...")
    ecs_cmd = [
        "aws", "ecs", "update-service",
        "--cluster", config.ecs.cluster_name,
        "--service", config.ecs.service_name,
        "--force-new-deployment",
        "--region", config.aws.region
    ]
    run_command(aws_cmd(ecs_cmd))

    click.echo(click.style(f"  Backend deployed successfully! (tag: {timestamp})", fg="green"))
    return True


def deploy_frontend(config: Config) -> bool:
    """Build and deploy frontend to S3."""
    click.echo(click.style("\n[Frontend] Building and deploying to S3...", fg="blue", bold=True))

    frontend_dir = config.frontend_dir

    if not frontend_dir.exists():
        raise click.ClickException(f"Frontend directory not found: {frontend_dir}")

    # Check if S3 bucket is configured
    if not config.s3.bucket_name:
        raise click.ClickException("S3 bucket not configured. Run 'ops deploy infra' first.")

    # Build AWS CLI command with profile if set
    def aws_cmd(base_cmd: list) -> list:
        if config.aws.profile:
            return base_cmd + ["--profile", config.aws.profile]
        return base_cmd

    # Install dependencies (use npm install as fallback if npm ci fails due to locks)
    click.echo("  Installing dependencies...")
    node_modules = frontend_dir / "node_modules"
    if node_modules.exists():
        click.echo("  (node_modules exists, using npm install)")
        run_command(["npm", "install"], cwd=frontend_dir, check=False)
    else:
        run_command(["npm", "ci"], cwd=frontend_dir)

    # Build
    click.echo("  Building React application...")
    run_command(["npm", "run", "build"], cwd=frontend_dir)

    # Find build directory (could be 'build' or 'dist' depending on bundler)
    build_dir = frontend_dir / "build"
    if not build_dir.exists():
        build_dir = frontend_dir / "dist"
    if not build_dir.exists():
        raise click.ClickException("Build output directory not found (checked 'build' and 'dist')")

    # Sync to S3
    click.echo(f"  Syncing to S3 bucket: {config.s3.bucket_name}...")
    run_command(aws_cmd([
        "aws", "s3", "sync",
        str(build_dir),
        f"s3://{config.s3.bucket_name}",
        "--delete"
    ]))

    # Invalidate CloudFront cache if configured
    if config.s3.cloudfront_distribution_id:
        click.echo("  Invalidating CloudFront cache...")
        run_command(aws_cmd([
            "aws", "cloudfront", "create-invalidation",
            "--distribution-id", config.s3.cloudfront_distribution_id,
            "--paths", "/*"
        ]))

    click.echo(click.style("  Frontend deployed successfully!", fg="green"))
    return True


@click.group()
def deploy():
    """Deploy infrastructure and applications."""
    pass


@deploy.command()
@click.option('--auto-approve', '-y', is_flag=True, help='Auto-approve Terraform changes')
def infra(auto_approve: bool):
    """Deploy Terraform infrastructure."""
    config = get_config()
    deploy_infrastructure(config, auto_approve)


@deploy.command()
def backend():
    """Build and deploy backend to ECS."""
    config = get_config()
    deploy_backend(config)


@deploy.command()
def frontend():
    """Build and deploy frontend to S3."""
    config = get_config()
    deploy_frontend(config)


@deploy.command()
@click.option('--auto-approve', '-y', is_flag=True, help='Auto-approve Terraform changes')
@click.option('--skip-infra', is_flag=True, help='Skip infrastructure deployment')
def all(auto_approve: bool, skip_infra: bool):
    """Deploy everything (infrastructure + backend + frontend)."""
    config = get_config()

    click.echo(click.style("\n=== Parliament Full Stack Deployment ===", fg="cyan", bold=True))
    click.echo(f"  Environment: {config.environment}")
    click.echo(f"  Region: {config.aws.region}")
    click.echo(f"  Domain: {config.domain_name}")

    success = True

    # Infrastructure
    if not skip_infra:
        try:
            deploy_infrastructure(config, auto_approve)
            # Reload config to get new outputs
            from .config import load_config, _config
            globals()['_config'] = load_config()
            config = get_config()
        except Exception as e:
            click.echo(click.style(f"  Infrastructure deployment failed: {e}", fg="red"))
            success = False

    # Backend
    if success:
        try:
            deploy_backend(config)
        except Exception as e:
            click.echo(click.style(f"  Backend deployment failed: {e}", fg="red"))
            success = False

    # Frontend
    if success:
        try:
            deploy_frontend(config)
        except Exception as e:
            click.echo(click.style(f"  Frontend deployment failed: {e}", fg="red"))
            success = False

    if success:
        click.echo(click.style("\n=== Deployment Complete ===", fg="green", bold=True))
    else:
        click.echo(click.style("\n=== Deployment Failed ===", fg="red", bold=True))
        sys.exit(1)
