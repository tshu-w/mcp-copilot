import logging
from pathlib import Path

from mcp_server_copilot.router import Router
from mcp_server_copilot.server import serve

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="MCP Copilot Server")

    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=Router._default_config_path,
        help=f"Path to config file (default: {Router._default_config_path})",
    )

    args = parser.parse_args()
    serve(args.config)


if __name__ == "__main__":
    main()
