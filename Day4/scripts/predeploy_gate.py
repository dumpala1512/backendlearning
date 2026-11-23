"""Pre-Deployment Safety Gate Script (Option B: Programmatic Python Configuration).

Runs all safety checks programmatically using the predeploy-checker package
upon Docker container startup.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure root directory is on Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from predeploy_checker import PreDeployError, PreDeployRunner, load_env_file


def main() -> None:
    # 1. Load local .env if present
    env_file = ROOT_DIR / ".env"
    if env_file.is_file():
        load_env_file(env_file)

    # 2. Resolve database and redis URLs from environment or application settings
    db_url = os.environ.get("DATABASE_URL")
    redis_url = os.environ.get("REDIS_URL")

    custom_checks = []
    try:
        from app.core.config import settings
        if not db_url and settings.DATABASE_URL:
            db_url = settings.DATABASE_URL
        if not redis_url and settings.REDIS_URL:
            redis_url = settings.REDIS_URL

        from app.core.predeploy import check_aws_secrets, check_s3_storage
        custom_checks.extend([check_aws_secrets, check_s3_storage])
    except Exception as exc:
        print(f"[Notice] App settings initialization warning: {exc}")

    print("=== [Safety Gate] Starting Pre-Deployment Validation (Option B) ===")

    # 3. Configure the runner explicitly in Python code (Option B)
    runner = PreDeployRunner(
        required_env_vars=[
            "AWS_REGION",
            "AWS_SECRETS_NAME",
            "DB_HOST",
            "DB_PORT",
            "DB_USER",
            "DB_NAME",
            "DB_DRIVER",
            "S3_BUCKET_NAME",
        ],
        check_database=bool(db_url),
        database_url=db_url,
        check_redis=bool(redis_url),
        redis_url=redis_url,
        run_tests=False,
        custom_checks=custom_checks,
        verbose=True,
    )

    # 4. Execute validation
    try:
        runner.run()
        print("\n=== [READY] All pre-deployment checks passed successfully! ===")
    except PreDeployError as err:
        print(f"\n[BLOCKED] Gate failed: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
