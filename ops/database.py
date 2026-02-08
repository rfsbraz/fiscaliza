"""
Database management commands for Parliament Operations CLI.

Handles database clearing, resetting, and maintenance operations.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from urllib.parse import quote_plus

import click

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from .config import get_config


def get_terraform_output(terraform_dir: Path, output_name: str) -> str:
    """Get a specific terraform output value."""
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


def get_production_db_url(config) -> tuple[str, dict]:
    """Get database URL from AWS Secrets Manager for production."""
    import boto3

    # Get secret ARN from terraform
    secret_arn = get_terraform_output(config.terraform_dir, "database_secret_arn")
    if not secret_arn:
        raise click.ClickException("Could not get database_secret_arn from terraform outputs")

    # Get credentials from Secrets Manager
    session = boto3.Session(profile_name=config.aws.profile, region_name=config.aws.region)
    client = session.client('secretsmanager')

    response = client.get_secret_value(SecretId=secret_arn)
    secret = json.loads(response['SecretString'])

    host = secret.get('host')
    port = secret.get('port', 5432)
    username = secret.get('username')
    password = secret.get('password')
    database = secret.get('database', 'parliament')

    # Handle host that already includes port (e.g., "host.rds.amazonaws.com:5432")
    if host and ':' in str(host):
        host_parts = str(host).split(':')
        host = host_parts[0]
        if len(host_parts) > 1:
            try:
                port = int(host_parts[1])
            except ValueError:
                port = 5432

    # Handle port if it's a string with duplicates (e.g., "5432:5432")
    if isinstance(port, str):
        port_str = port.split(':')[0] if ':' in port else port
        try:
            port = int(port_str.strip())
        except ValueError:
            port = 5432
    elif not isinstance(port, int):
        port = 5432

    encoded_password = quote_plus(password)
    db_url = f"postgresql://{username}:{encoded_password}@{host}:{port}/{database}?sslmode=require"

    info = {
        'source': 'AWS Secrets Manager (production)',
        'host': host,
        'port': port,
        'database': database,
        'username': username
    }

    return db_url, info


def create_production_engine(config, echo: bool = False):
    """Create database engine for production RDS."""
    from sqlalchemy import create_engine

    db_url, _ = get_production_db_url(config)

    return create_engine(
        db_url,
        echo=echo,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        connect_args={
            'connect_timeout': 30,
            'sslmode': 'require'
        }
    )


def get_db_connection_info(production: bool = False):
    """Get database connection information for display."""
    if production:
        try:
            config = get_config()
            _, info = get_production_db_url(config)
            return info
        except Exception as e:
            return {
                'source': 'Production (error)',
                'host': 'Unknown',
                'database': 'Unknown',
                'error': str(e)
            }

    try:
        from database.connection import DATABASE_SECRET_ARN, PG_HOST, PG_DATABASE

        if DATABASE_SECRET_ARN:
            return {
                'source': 'AWS Secrets Manager',
                'host': 'RDS (from secrets)',
                'database': 'parliament'
            }
        else:
            return {
                'source': 'Local (environment variables)',
                'host': PG_HOST,
                'database': PG_DATABASE
            }
    except Exception as e:
        return {
            'source': 'Unknown',
            'host': 'Unknown',
            'database': 'Unknown',
            'error': str(e)
        }


def clear_all_tables(engine, echo: bool = False, exclude_tables: list = None):
    """Clear all data from tables without dropping them.

    Args:
        engine: SQLAlchemy engine
        echo: Print progress messages
        exclude_tables: List of table names to skip (e.g., ['import_status'])
    """
    from sqlalchemy import text, MetaData

    exclude_tables = exclude_tables or []
    # Always preserve alembic_version to maintain migration state
    if 'alembic_version' not in exclude_tables:
        exclude_tables.append('alembic_version')

    metadata = MetaData()
    metadata.reflect(bind=engine)

    # Get tables in reverse dependency order (to handle foreign keys)
    tables = list(reversed(metadata.sorted_tables))

    cleared_count = 0
    with engine.begin() as conn:
        # Disable foreign key checks temporarily for PostgreSQL
        conn.execute(text("SET session_replication_role = 'replica';"))

        for table in tables:
            if table.name in exclude_tables:
                if echo:
                    click.echo(f"    Skipping table: {table.name} (excluded)")
                continue
            if echo:
                click.echo(f"    Clearing table: {table.name}")
            conn.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))
            cleared_count += 1

        # Re-enable foreign key checks
        conn.execute(text("SET session_replication_role = 'origin';"))

    return cleared_count


def drop_all_tables(engine, echo: bool = False):
    """Drop all tables including alembic_version.

    Alembic will recreate alembic_version when running migrations.
    Returns the number of tables dropped.
    """
    from sqlalchemy import text, MetaData

    metadata = MetaData()
    metadata.reflect(bind=engine)

    # Get tables in reverse dependency order (to handle foreign keys)
    tables = list(reversed(metadata.sorted_tables))

    dropped_count = 0
    with engine.begin() as conn:
        # Disable foreign key checks temporarily
        conn.execute(text("SET session_replication_role = 'replica';"))

        for table in tables:
            if echo:
                click.echo(f"    Dropping table: {table.name}")
            conn.execute(text(f'DROP TABLE IF EXISTS "{table.name}" CASCADE'))
            dropped_count += 1

        # Re-enable foreign key checks
        conn.execute(text("SET session_replication_role = 'origin';"))

    return dropped_count


def drop_and_recreate_tables(engine, echo: bool = False):
    """Drop all tables and recreate them from models.

    DEPRECATED: Use drop_all_tables_except_alembic + run migrations instead.
    """
    from database.models import Base

    if echo:
        click.echo("    Dropping all tables...")

    Base.metadata.drop_all(bind=engine)

    if echo:
        click.echo("    Creating tables from models...")

    Base.metadata.create_all(bind=engine)

    return len(Base.metadata.tables)


def reset_import_status(engine, echo: bool = False):
    """Reset all import status records to 'discovered' state."""
    from sqlalchemy import text

    with engine.begin() as conn:
        # Check if import_status table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'import_status'
            )
        """))
        if not result.scalar():
            if echo:
                click.echo("    import_status table does not exist, skipping...")
            return 0

        # Get count before reset
        count_result = conn.execute(text("SELECT COUNT(*) FROM import_status WHERE status != 'discovered'"))
        count = count_result.scalar()

        if count == 0:
            if echo:
                click.echo("    No import status records to reset")
            return 0

        # Reset all records
        conn.execute(text("""
            UPDATE import_status
            SET
                status = 'discovered',
                processing_started_at = NULL,
                processing_completed_at = NULL,
                error_message = NULL,
                records_imported = 0,
                error_count = 0,
                retry_at = NULL,
                updated_at = NOW()
            WHERE status != 'discovered'
        """))

        if echo:
            click.echo(f"    Reset {count} import status records to 'discovered'")

        return count


def get_engine(production: bool, verbose: bool):
    """Get database engine based on production flag."""
    if production:
        config = get_config()
        return create_production_engine(config, echo=verbose)
    else:
        from database.connection import create_database_engine
        return create_database_engine(echo=verbose)


def run_alembic_command(args: list[str], db_url: str = None, verbose: bool = False) -> subprocess.CompletedProcess:
    """Run an alembic command with optional database URL override."""
    cmd = ["alembic"] + args

    env = os.environ.copy()
    if db_url:
        env["DATABASE_URL"] = db_url

    if verbose:
        click.echo(f"  $ {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        cwd=project_root,
        capture_output=True,
        text=True,
        env=env
    )

    return result


def get_current_revision(db_url: str = None, verbose: bool = False) -> str:
    """Get current alembic revision from database."""
    result = run_alembic_command(["current"], db_url=db_url, verbose=verbose)
    if result.returncode == 0:
        # Parse output like "a1b2c3d4e5f6 (head)" or just revision id
        output = result.stdout.strip()
        if output:
            # Extract just the revision id
            return output.split()[0] if output else "None"
    return "Unknown"


def get_pending_migrations(db_url: str = None, verbose: bool = False) -> list[str]:
    """Get list of pending migrations."""
    result = run_alembic_command(["history", "--indicate-current"], db_url=db_url, verbose=verbose)
    if result.returncode != 0:
        return []

    pending = []
    current_found = False
    for line in result.stdout.strip().split('\n'):
        if '(current)' in line or '(head)' in line:
            current_found = True
            if '(current)' in line and '(head)' not in line:
                # There are migrations after current
                continue
        elif current_found:
            continue
        elif line.strip() and '->' in line:
            # This is a pending migration (before current marker)
            pending.append(line.strip())

    return pending


@click.group()
def database():
    """Database management commands."""
    pass


@database.command()
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt')
@click.option('--preserve-schema', is_flag=True, help='Keep tables, only clear data')
@click.option('--keep-downloads', is_flag=True, help='Preserve download state (reset import_status instead of truncating)')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed progress')
@click.option('--production', '-p', is_flag=True, help='Connect to production RDS database')
def clear(yes: bool, preserve_schema: bool, keep_downloads: bool, verbose: bool, production: bool):
    """
    Clear all data from the database.

    By default, drops all tables and recreates them by running migrations.
    Alembic automatically recreates its tracking table during migration.

    Use --preserve-schema to only truncate data while keeping table structure.
    This preserves alembic_version to maintain migration state.

    Use --keep-downloads to preserve import_status records (reset to 'discovered' state)
        so that already-downloaded files are not re-downloaded after a wipe.
    Use --production to connect to the production RDS database.
    """
    click.echo(click.style("\n[Database] Clear Database", fg="blue", bold=True))

    # Show connection info
    info = get_db_connection_info(production=production)
    click.echo(f"  Source: {info['source']}")
    click.echo(f"  Host: {info['host']}")
    click.echo(f"  Database: {info['database']}")

    if 'error' in info:
        raise click.ClickException(f"Could not get database info: {info['error']}")

    # Extra warning for production
    if production:
        click.echo(click.style("\n  ⚠️  WARNING: You are about to modify PRODUCTION database!", fg="red", bold=True))

    # Confirmation
    if not yes:
        action = "truncate all tables" if preserve_schema else "drop and recreate all tables"
        if keep_downloads:
            action += " (preserving import_status)"
        if not click.confirm(click.style(f"\n  WARNING: This will {action}. Continue?", fg="yellow")):
            click.echo("  Aborted.")
            return

    try:
        engine = get_engine(production, verbose)

        if preserve_schema:
            click.echo("\n  Truncating all tables...")
            exclude_tables = ['import_status'] if keep_downloads else []
            count = clear_all_tables(engine, echo=verbose, exclude_tables=exclude_tables)
            click.echo(click.style(f"\n  Cleared {count} tables successfully!", fg="green"))

            if keep_downloads:
                click.echo("\n  Resetting import_status records...")
                reset_count = reset_import_status(engine, echo=verbose)
                if reset_count > 0:
                    click.echo(click.style(f"  Reset {reset_count} import records to 'discovered' state", fg="cyan"))
                else:
                    click.echo(click.style("  No import records needed reset", fg="cyan"))
        else:
            if keep_downloads:
                click.echo(click.style("\n  Note: --keep-downloads requires --preserve-schema", fg="yellow"))
                click.echo("  Falling back to preserve-schema mode...")
                exclude_tables = ['import_status']
                count = clear_all_tables(engine, echo=verbose, exclude_tables=exclude_tables)
                click.echo(click.style(f"\n  Cleared {count} tables successfully!", fg="green"))

                click.echo("\n  Resetting import_status records...")
                reset_count = reset_import_status(engine, echo=verbose)
                if reset_count > 0:
                    click.echo(click.style(f"  Reset {reset_count} import records to 'discovered' state", fg="cyan"))
            else:
                # Drop all tables (alembic will recreate alembic_version)
                click.echo("\n  Dropping all tables...")
                count = drop_all_tables(engine, echo=verbose)
                click.echo(click.style(f"\n  Dropped {count} tables.", fg="cyan"))

                # Run migrations to recreate tables
                click.echo("\n  Running migrations to recreate tables...")
                db_url = None
                if production:
                    config = get_config()
                    db_url, _ = get_production_db_url(config)

                result = run_alembic_command(["upgrade", "head"], db_url=db_url, verbose=True)

                if result.returncode == 0:
                    click.echo(click.style("\n  Tables recreated successfully via migrations!", fg="green"))
                    if result.stdout:
                        for line in result.stdout.strip().split('\n'):
                            if line.strip():
                                click.echo(f"    {line}")
                else:
                    click.echo(click.style("\n  Migration failed!", fg="red"))
                    if result.stderr:
                        for line in result.stderr.strip().split('\n'):
                            click.echo(f"    {line}")
                    raise click.ClickException("Failed to recreate tables via migrations")

    except Exception as e:
        raise click.ClickException(f"Database operation failed: {e}")


@database.command()
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed progress')
@click.option('--production', '-p', is_flag=True, help='Connect to production RDS database')
def reset_imports(yes: bool, verbose: bool, production: bool):
    """
    Reset all import status records to 'discovered' state.

    This allows all files to be re-imported by the pipeline.
    Use --production to connect to the production RDS database.
    """
    click.echo(click.style("\n[Database] Reset Import Status", fg="blue", bold=True))

    # Show connection info
    info = get_db_connection_info(production=production)
    click.echo(f"  Source: {info['source']}")
    click.echo(f"  Host: {info['host']}")
    click.echo(f"  Database: {info['database']}")

    # Extra warning for production
    if production:
        click.echo(click.style("\n  ⚠️  WARNING: You are about to modify PRODUCTION database!", fg="red", bold=True))

    # Confirmation
    if not yes:
        if not click.confirm(click.style("\n  This will reset all import status records. Continue?", fg="yellow")):
            click.echo("  Aborted.")
            return

    try:
        engine = get_engine(production, verbose)
        count = reset_import_status(engine, echo=verbose)

        if count > 0:
            click.echo(click.style(f"\n  Reset {count} import status records!", fg="green"))
        else:
            click.echo(click.style("\n  No records needed to be reset.", fg="cyan"))

    except Exception as e:
        raise click.ClickException(f"Reset failed: {e}")


@database.command()
@click.option('--verbose', '-v', is_flag=True, help='Show detailed table information')
@click.option('--production', '-p', is_flag=True, help='Connect to production RDS database')
def status(verbose: bool, production: bool):
    """Show database status and table statistics."""
    from sqlalchemy import text, MetaData

    click.echo(click.style("\n[Database] Status", fg="blue", bold=True))

    # Show connection info
    info = get_db_connection_info(production=production)
    click.echo(f"\n  Connection: {info['source']}")
    click.echo(f"  Host: {info['host']}")
    click.echo(f"  Database: {info['database']}")

    if 'error' in info:
        raise click.ClickException(f"Could not get database info: {info['error']}")

    try:
        engine = get_engine(production, verbose=False)
        metadata = MetaData()
        metadata.reflect(bind=engine)

        click.echo(f"\n  Tables: {len(metadata.tables)}")

        if verbose:
            click.echo("\n  Table row counts:")
            with engine.connect() as conn:
                for table in sorted(metadata.tables.keys()):
                    try:
                        result = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                        count = result.scalar()
                        if count > 0:
                            click.echo(f"    {table}: {count:,} rows")
                    except Exception:
                        click.echo(f"    {table}: (error reading)")

        # Check import status if table exists
        if 'import_status' in metadata.tables:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT status, COUNT(*) as count
                    FROM import_status
                    GROUP BY status
                    ORDER BY count DESC
                """))
                rows = result.fetchall()

                if rows:
                    click.echo("\n  Import status:")
                    for row in rows:
                        click.echo(f"    {row[0]}: {row[1]:,}")

                # Processing time statistics
                time_result = conn.execute(text("""
                    SELECT
                        COUNT(*) FILTER (WHERE processing_duration_seconds IS NOT NULL) as processed_count,
                        SUM(processing_duration_seconds) as total_seconds,
                        AVG(processing_duration_seconds) as avg_seconds,
                        MIN(processing_duration_seconds) as min_seconds,
                        MAX(processing_duration_seconds) as max_seconds,
                        MIN(processing_started_at) as first_started,
                        MAX(processing_completed_at) as last_completed
                    FROM import_status
                    WHERE processing_duration_seconds IS NOT NULL
                """))
                time_row = time_result.fetchone()

                if time_row and time_row[0] and time_row[0] > 0:
                    click.echo("\n  Processing time:")
                    processed_count = time_row[0]
                    total_seconds = time_row[1] or 0
                    avg_seconds = time_row[2] or 0
                    min_seconds = time_row[3] or 0
                    max_seconds = time_row[4] or 0
                    first_started = time_row[5]
                    last_completed = time_row[6]

                    # Format total time
                    hours, remainder = divmod(int(total_seconds), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    if hours > 0:
                        total_fmt = f"{hours}h {minutes}m {seconds}s"
                    elif minutes > 0:
                        total_fmt = f"{minutes}m {seconds}s"
                    else:
                        total_fmt = f"{total_seconds:.1f}s"

                    click.echo(f"    Files processed: {processed_count:,}")
                    click.echo(f"    Total time: {total_fmt}")
                    click.echo(f"    Avg per file: {avg_seconds:.2f}s")
                    click.echo(f"    Min/Max: {min_seconds:.2f}s / {max_seconds:.2f}s")

                    if first_started and last_completed:
                        # Calculate wall clock time
                        wall_time = (last_completed - first_started).total_seconds()
                        wall_hours, wall_remainder = divmod(int(wall_time), 3600)
                        wall_minutes, wall_seconds = divmod(wall_remainder, 60)
                        if wall_hours > 0:
                            wall_fmt = f"{wall_hours}h {wall_minutes}m {wall_seconds}s"
                        elif wall_minutes > 0:
                            wall_fmt = f"{wall_minutes}m {wall_seconds}s"
                        else:
                            wall_fmt = f"{wall_time:.1f}s"
                        click.echo(f"    Wall clock: {wall_fmt}")
                        click.echo(f"    Started: {first_started.strftime('%Y-%m-%d %H:%M:%S')}")
                        click.echo(f"    Completed: {last_completed.strftime('%Y-%m-%d %H:%M:%S')}")

        click.echo(click.style("\n  Database connection OK", fg="green"))

    except Exception as e:
        raise click.ClickException(f"Could not connect to database: {e}")


@database.command()
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed progress')
@click.option('--production', '-p', is_flag=True, help='Connect to production RDS database')
@click.option('--revision', '-r', default='head', help='Target revision (default: head)')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
def migrate(yes: bool, verbose: bool, production: bool, revision: str, dry_run: bool):
    """
    Run database migrations using Alembic.

    Applies pending migrations to bring the database schema up to date.
    Use --production to run against the production RDS database.
    Use --dry-run to see what migrations would be applied.

    Examples:
        ops database migrate              # Migrate local database
        ops database migrate -p           # Migrate production database
        ops database migrate --dry-run    # Show pending migrations
        ops database migrate -r abc123    # Migrate to specific revision
    """
    click.echo(click.style("\n[Database] Run Migrations", fg="blue", bold=True))

    # Get database URL
    db_url = None
    if production:
        try:
            config = get_config()
            db_url, info = get_production_db_url(config)
        except Exception as e:
            raise click.ClickException(f"Could not get production database URL: {e}")
    else:
        info = get_db_connection_info(production=False)

    # Show connection info
    click.echo(f"\n  Connection: {info['source']}")
    click.echo(f"  Host: {info['host']}")
    click.echo(f"  Database: {info.get('database', 'parliament')}")

    # Show current state
    click.echo(f"\n  Current revision: {get_current_revision(db_url, verbose)}")
    click.echo(f"  Target revision: {revision}")

    # Check what migrations would run
    result = run_alembic_command(["history", "-r", "current:head", "--verbose"], db_url=db_url, verbose=verbose)

    if result.returncode != 0:
        # If current is not set, show all migrations
        result = run_alembic_command(["history", "--verbose"], db_url=db_url, verbose=verbose)

    pending_output = result.stdout.strip() if result.returncode == 0 else ""

    if not pending_output or "head" in get_current_revision(db_url, verbose).lower():
        click.echo(click.style("\n  Database is up to date - no migrations needed.", fg="green"))
        return

    click.echo("\n  Pending migrations:")
    for line in pending_output.split('\n')[:10]:  # Show first 10 lines
        if line.strip():
            click.echo(f"    {line.strip()}")

    if dry_run:
        click.echo(click.style("\n  Dry run complete - no changes made.", fg="cyan"))
        return

    # Extra warning for production
    if production:
        click.echo(click.style("\n  ⚠️  WARNING: You are about to migrate PRODUCTION database!", fg="red", bold=True))

    # Confirmation
    if not yes:
        if not click.confirm(click.style(f"\n  Apply migrations to {revision}?", fg="yellow")):
            click.echo("  Aborted.")
            return

    # Run migration
    click.echo(f"\n  Running: alembic upgrade {revision}")

    result = run_alembic_command(["upgrade", revision], db_url=db_url, verbose=True)

    if result.returncode == 0:
        click.echo(click.style("\n  Migrations applied successfully!", fg="green"))
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                click.echo(f"    {line}")
        click.echo(f"\n  New revision: {get_current_revision(db_url, verbose)}")
    else:
        click.echo(click.style("\n  Migration failed!", fg="red"))
        if result.stderr:
            click.echo(f"\n  Error output:")
            for line in result.stderr.strip().split('\n'):
                click.echo(f"    {line}")
        if result.stdout:
            click.echo(f"\n  Output:")
            for line in result.stdout.strip().split('\n'):
                click.echo(f"    {line}")
        raise click.ClickException("Migration failed")


@database.command()
@click.option('--verbose', '-v', is_flag=True, help='Show detailed information')
@click.option('--production', '-p', is_flag=True, help='Connect to production RDS database')
def migration_status(verbose: bool, production: bool):
    """
    Show current migration status and history.

    Displays the current revision and available migrations.
    Use --production to check the production database.
    """
    click.echo(click.style("\n[Database] Migration Status", fg="blue", bold=True))

    # Get database URL
    db_url = None
    if production:
        try:
            config = get_config()
            db_url, info = get_production_db_url(config)
        except Exception as e:
            raise click.ClickException(f"Could not get production database URL: {e}")
    else:
        info = get_db_connection_info(production=False)

    # Show connection info
    click.echo(f"\n  Connection: {info['source']}")
    click.echo(f"  Host: {info['host']}")
    click.echo(f"  Database: {info.get('database', 'parliament')}")

    # Get current revision
    current = get_current_revision(db_url, verbose)
    click.echo(f"\n  Current revision: {current}")

    # Get head revision
    result = run_alembic_command(["heads"], db_url=db_url, verbose=verbose)
    if result.returncode == 0:
        head = result.stdout.strip().split()[0] if result.stdout.strip() else "Unknown"
        click.echo(f"  Head revision: {head}")

        if current == head or "(head)" in current:
            click.echo(click.style("\n  Status: Up to date", fg="green"))
        else:
            click.echo(click.style("\n  Status: Migrations pending", fg="yellow"))

    if verbose:
        click.echo("\n  Migration history:")
        result = run_alembic_command(["history", "--indicate-current"], db_url=db_url, verbose=verbose)
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    # Highlight current revision
                    if '(current)' in line:
                        click.echo(click.style(f"    {line.strip()}", fg="cyan"))
                    else:
                        click.echo(f"    {line.strip()}")
