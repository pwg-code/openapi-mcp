"""CLI entry point for openapi-mcp."""

import argparse
import asyncio
import sys


def main():
    parser = argparse.ArgumentParser(prog="openapi-mcp", description="OpenAPI MCP Server")
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Start MCP server")
    serve_parser.add_argument(
        "--url", action="append", metavar="NAME=URL",
        help="Remote OpenAPI spec (e.g. --url local-api=http://localhost:8000/openapi.json). Can be repeated.",
    )
    serve_parser.add_argument(
        "--file", action="append", metavar="NAME=PATH",
        help="Local OpenAPI spec file (e.g. --file petstore=./petstore.json). Can be repeated.",
    )
    serve_parser.add_argument("--refresh-interval", type=int, default=300, help="Refresh interval in seconds (default: 300)")
    serve_parser.add_argument("--request-timeout", type=int, default=30, help="Request timeout in seconds (default: 30)")

    subparsers.add_parser("status", help="Show project status")

    args = parser.parse_args()

    if args.command == "serve":
        if not args.url and not args.file:
            parser.error("At least one --url or --file is required")

        from openapi_mcp_server.config import build_config
        from openapi_mcp_server.server import run_server

        config = build_config(
            urls=args.url or [],
            files=args.file or [],
            refresh_interval=args.refresh_interval,
            request_timeout=args.request_timeout,
        )
        asyncio.run(run_server(config))
    elif args.command == "status":
        print("Status command not yet implemented. Use 'openapi-mcp serve' to start the server.")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
