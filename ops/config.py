"""
Configuration loader for Parliament Operations CLI.

Loads configuration from terraform.tfvars and environment variables.
"""

import os
import re
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AWSConfig:
    """AWS configuration."""
    region: str = "eu-west-1"
    account_id: Optional[str] = None
    profile: Optional[str] = None


@dataclass
class ECSConfig:
    """ECS configuration."""
    cluster_name: str = ""
    service_name: str = ""


@dataclass
class ECRConfig:
    """ECR configuration."""
    repository_url: str = ""
    repository_name: str = "parliament-app"


@dataclass
class S3Config:
    """S3 configuration."""
    bucket_name: str = ""
    cloudfront_distribution_id: str = ""


@dataclass
class PipelineConfig:
    """Pipeline configuration."""
    lambda_function_url: str = ""
    spot_instance_type: str = "t3.large"
    timeout_minutes: int = 500


@dataclass
class Config:
    """Main configuration container."""
    project_name: str = "parliament"
    environment: str = "prod"
    domain_name: str = "fiscaliza.pt"

    aws: AWSConfig = field(default_factory=AWSConfig)
    ecs: ECSConfig = field(default_factory=ECSConfig)
    ecr: ECRConfig = field(default_factory=ECRConfig)
    s3: S3Config = field(default_factory=S3Config)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)

    # Paths
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    terraform_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "terraform")
    frontend_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "frontend")


def parse_tfvars(filepath: Path) -> dict:
    """Parse terraform.tfvars file into a dictionary."""
    if not filepath.exists():
        return {}

    result = {}
    content = filepath.read_text(encoding='utf-8')

    # Remove comments
    lines = []
    for line in content.split('\n'):
        # Remove inline comments
        if '#' in line:
            line = line[:line.index('#')]
        lines.append(line)
    content = '\n'.join(lines)

    # Parse simple key = value pairs
    pattern = r'^(\w+)\s*=\s*"([^"]*)"'
    for match in re.finditer(pattern, content, re.MULTILINE):
        result[match.group(1)] = match.group(2)

    # Parse boolean values
    pattern = r'^(\w+)\s*=\s*(true|false)'
    for match in re.finditer(pattern, content, re.MULTILINE):
        result[match.group(1)] = match.group(2) == 'true'

    # Parse numeric values
    pattern = r'^(\w+)\s*=\s*(\d+)'
    for match in re.finditer(pattern, content, re.MULTILINE):
        result[match.group(1)] = int(match.group(2))

    return result


def get_terraform_output(terraform_dir: Path, output_name: str) -> Optional[str]:
    """Get a Terraform output value."""
    import subprocess
    try:
        result = subprocess.run(
            ["terraform", "output", "-raw", output_name],
            cwd=terraform_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_aws_profiles() -> list:
    """Get list of available AWS profiles."""
    import subprocess
    try:
        result = subprocess.run(
            ["aws", "configure", "list-profiles"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return [p.strip() for p in result.stdout.strip().split('\n') if p.strip()]
    except Exception:
        pass
    return []


def get_aws_account_id(profile: Optional[str] = None) -> Optional[str]:
    """Get AWS account ID from STS."""
    import subprocess
    try:
        cmd = ["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"]
        if profile:
            cmd.extend(["--profile", profile])
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def load_config() -> Config:
    """Load configuration from all sources."""
    config = Config()

    # Load from terraform.tfvars
    tfvars = parse_tfvars(config.terraform_dir / "terraform.tfvars")

    # Apply tfvars values
    config.environment = tfvars.get('environment', config.environment)
    config.domain_name = tfvars.get('domain_name', config.domain_name)
    config.aws.region = tfvars.get('aws_region', config.aws.region)
    config.pipeline.spot_instance_type = tfvars.get('spot_instance_type', config.pipeline.spot_instance_type)
    config.pipeline.timeout_minutes = tfvars.get('import_timeout_minutes', config.pipeline.timeout_minutes)

    # Check for AWS profile - first from env, then from tfvars, then auto-detect
    config.aws.profile = os.environ.get('AWS_PROFILE') or tfvars.get('aws_profile')

    # If no profile set, try to find one that works
    if not config.aws.profile:
        profiles = get_aws_profiles()
        for profile in profiles:
            if get_aws_account_id(profile):
                config.aws.profile = profile
                break

    # Get AWS account ID using the profile
    config.aws.account_id = get_aws_account_id(config.aws.profile)

    # Build derived values
    name_prefix = f"fiscaliza-{config.environment}"

    config.ecs.cluster_name = f"{name_prefix}-cluster"
    config.ecs.service_name = f"{name_prefix}-backend-service"
    config.ecr.repository_name = "parliament-app"

    if config.aws.account_id:
        config.ecr.repository_url = f"{config.aws.account_id}.dkr.ecr.{config.aws.region}.amazonaws.com/{config.ecr.repository_name}"

    # Try to get values from Terraform outputs
    ecr_url = get_terraform_output(config.terraform_dir, "ecr_repository_url")
    if ecr_url:
        config.ecr.repository_url = ecr_url
        # Extract account ID from ECR URL if not already set
        if not config.aws.account_id and '.dkr.ecr.' in ecr_url:
            config.aws.account_id = ecr_url.split('.')[0]

    s3_bucket = get_terraform_output(config.terraform_dir, "s3_bucket_name")
    if s3_bucket:
        config.s3.bucket_name = s3_bucket

    cf_dist = get_terraform_output(config.terraform_dir, "cloudfront_distribution_id")
    if cf_dist and cf_dist != "CloudFront not enabled":
        config.s3.cloudfront_distribution_id = cf_dist

    lambda_url = get_terraform_output(config.terraform_dir, "spot_import_function_url")
    if lambda_url and lambda_url != "Not enabled":
        config.pipeline.lambda_function_url = lambda_url

    return config


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create the global config instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config
