#!/usr/bin/env python3
"""Entry point for the Amarisoft REST API webservice.

Run the service with:
    python -m service.main

Or with uvicorn directly:
    uvicorn service.app:create_app --factory --host 0.0.0.0 --port 8080

Environment variables:
    See service/config.py for all configuration options.
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    """Run the Amarisoft REST API service.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    # Import here to avoid import errors when just checking --help
    import uvicorn

    from .app import create_app
    from .config import Settings, get_settings

    parser = argparse.ArgumentParser(
        description="Amarisoft REST API Webservice",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Host to bind to (overrides AMARISOFT_API_HOST env var)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to listen on (overrides AMARISOFT_API_PORT env var)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        default=None,
        help="Log level (overrides AMARISOFT_LOG_LEVEL env var)",
    )
    parser.add_argument(
        "--callbox-host",
        default=None,
        help="Callbox host (overrides AMARISOFT_CALLBOX_HOST env var)",
    )

    args = parser.parse_args()

    # Load base settings from environment
    settings = get_settings()

    # Override with command line arguments
    host = args.host or settings.host
    port = args.port or settings.port
    log_level = (args.log_level or settings.log_level).lower()

    # If callbox host is overridden, we need to create new settings
    if args.callbox_host:
        # Create new settings with overridden callbox_host
        import os

        os.environ["AMARISOFT_CALLBOX_HOST"] = args.callbox_host
        # Clear cache and reload
        get_settings.cache_clear()
        settings = get_settings()

    print(f"Starting Amarisoft REST API on {host}:{port}")
    print(f"Callbox host: {settings.callbox_host}")
    print(f"Log level: {log_level}")
    print(f"API docs: http://{host}:{port}/docs")
    print()

    try:
        uvicorn.run(
            "service.app:create_app",
            factory=True,
            host=host,
            port=port,
            log_level=log_level,
            reload=args.reload,
        )
        return 0
    except KeyboardInterrupt:
        print("\nShutting down...")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
