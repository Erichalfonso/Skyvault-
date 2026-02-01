#!/usr/bin/env python
"""
Test runner script for Skyvault KYC project.

Usage:
    python scripts/run_tests.py             # Run all tests
    python scripts/run_tests.py unit        # Run only unit tests
    python scripts/run_tests.py integration # Run only integration tests
    python scripts/run_tests.py coverage    # Run tests with coverage report
"""

import subprocess
import sys
from pathlib import Path

# Ensure we're in the project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "app"))


def run_command(cmd: list[str]) -> int:
    """Run a command and return exit code."""
    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print("=" * 60)
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode


def main():
    args = sys.argv[1:]

    if not args or args[0] == "all":
        # Run all tests
        return run_command([
            "python", "-m", "pytest", "tests/", "-v", "--tb=short"
        ])

    elif args[0] == "unit":
        # Run only unit tests
        return run_command([
            "python", "-m", "pytest", "tests/", "-v", "-m", "unit"
        ])

    elif args[0] == "integration":
        # Run only integration tests
        return run_command([
            "python", "-m", "pytest", "tests/", "-v", "-m", "integration"
        ])

    elif args[0] == "coverage":
        # Run with coverage
        return run_command([
            "python", "-m", "pytest", "tests/",
            "--cov=app",
            "--cov-report=term-missing",
            "--cov-report=html:coverage_html",
            "-v"
        ])

    elif args[0] == "fast":
        # Run tests in parallel (requires pytest-xdist)
        return run_command([
            "python", "-m", "pytest", "tests/", "-v", "-x", "--tb=short"
        ])

    elif args[0] == "watch":
        # Watch mode (requires pytest-watch)
        return run_command([
            "python", "-m", "pytest_watch", "--", "-v", "--tb=short"
        ])

    elif args[0] == "lint":
        # Run linter
        return run_command([
            "python", "-m", "ruff", "check", "app/", "tests/"
        ])

    elif args[0] == "format":
        # Run formatter
        return run_command([
            "python", "-m", "ruff", "format", "app/", "tests/"
        ])

    else:
        print(f"Unknown command: {args[0]}")
        print(__doc__)
        return 1


if __name__ == "__main__":
    sys.exit(main())
