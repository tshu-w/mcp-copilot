import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import mcp.types as types
import yaml

from mcp_server_copilot.mcp_connection import MCPConnection
from mcp_server_copilot.retriever import SparseRetriever
from mcp_server_copilot.schemas import Server, ServerConfig

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "mcpServers": {
        "everything": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-everything"],
        },
        "fetch": {"command": "uvx", "args": ["mcp-server-fetch"]},
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
        },
        "git": {"command": "uvx", "args": ["mcp-server-git"]},
        "github": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "<YOUR_TOKEN>"},
        },
        "memory": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"],
        },
        "postgres": {
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-postgres",
                "postgresql://localhost/mydb",
            ],
        },
        "puppeteer": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
        },
        "sequential-thinking": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
        },
        # "time": {
        #     "command": "uvx",
        #     "args": ["mcp-server-time"]
        # }
    }
}


def dump_to_yaml(data: dict[str, Any]) -> str:
    """
    Convert a Python object to a YAML string.

    Args:
        data (dict[str, Any]): The Python dict to dump.

    Returns:
        str: The YAML string representation of the object.
    """
    return yaml.dump(
        data,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )


class Router:
    """
    A Router that aggregates multiple MCP servers.
    """

    _default_config_path = (
        Path.home() / ".config" / "mcp-server-copilot" / "config.json"
    )

    def __init__(
        self,
        config: dict[str, Any] | Path = _default_config_path,
    ):
        """
        Initialize the Router with a configuration.

        Args:
            config (dict[str, Any] | Path): A dictionary of configurations
                                            or a path to the JSON configuration file.
                                            Defaults to ~/.config/mcp/config.json.
        """
        self.connections = {}

        if isinstance(config, dict):
            # If config is already a dictionary, use it directly
            self.config = config
        elif isinstance(config, Path):
            # If config is a Path, read the JSON file
            if config.exists():
                with config.open("r") as f:
                    self.config = json.load(f)
            else:
                self.config = DEFAULT_CONFIG
        else:
            raise ValueError("Config must be a dictionary or a Path to a JSON file.")

    async def initialize(self):
        """
        Initialize connections to all MCP servers specified in the configuration.
        Connections are established concurrently, and only successful connections are stored.
        """
        connections = {}
        for name, config in self.config["mcpServers"].items():
            server = Server(name=name, config=ServerConfig(**config))
            connection = MCPConnection(server)
            connections[name] = connection

        results = []
        for conn in connections.values():
            try:
                result = await conn.connect()
                results.append(result)
            except Exception as e:
                results.append(e)

        # Store only the connections that succeeded
        for name, result in zip(connections.keys(), results, strict=False):
            if not isinstance(result, Exception):
                self.connections[name] = connections[name]
            else:
                logger.error(f"Failed to connect to server {name}: {result}")

        self._servers = await self.get_servers()
        server_corpus = [
            {
                "id": key,
                "text": dump_to_yaml(server.model_dump()),
            }
            for key, server in self._servers.items()
        ]

        self._tools = await self.get_tools()
        tool_corpus = [
            {
                "id": key,
                "text": dump_to_yaml({"server_name": server} | tool.model_dump()),
            }
            for key, tool in self._tools.items()
        ]

        self._server_retriever = SparseRetriever().index(server_corpus)
        self._tool_retriever = SparseRetriever().index(tool_corpus)

    async def route_servers(self, query: str, top_k: int) -> types.CallToolResult:
        results = self._server_retriever.search(query, top_k)
        servers = [self._servers[res["doc_id"]] for res in results]
        server_dict = [server.model_dump() for server in servers]

        return dump_to_yaml({"mcpServers": server_dict})

    async def route_tools(self, query: str, top_k: int) -> types.CallToolResult:
        results = self._tool_retriever.search(query, top_k)

        tools = [self._tools[res["doc_id"]] for res in results]
        tool_dict = [
            {"server_name": res["doc_id"].split("/")[0]} | tool.model_dump()
            for res, tool in zip(results, tools, strict=False)
        ]

        return dump_to_yaml({"mcpTools": tool_dict})

    async def call_tool(
        self, server_name: str, tool_name: str, params: dict[str, Any] | None = None
    ) -> types.CallToolResult:
        """
        Call a specific tool on a specified server.

        Args:
            server_name (str): Name of the server to call the tool on.
            tool_name (str): Name of the tool to call.
            params (dict[str, Any] | None): Parameters for the tool, defaults to None.

        Returns:
            types.CallToolResult: The result of the tool execution.

        Raises:
            ValueError: If the server is not found or not connected.
        """
        if server_name not in self.connections:
            raise ValueError(f"Server {server_name} not found or not connected")

        try:
            connection = self.connections[server_name]
            return await connection.call_tool(tool_name, params or {})
        except Exception as e:
            logger.error(f"Error calling tool {tool_name} on server {server_name}: {e}")
            raise

    async def get_tools(
        self, server_name: str | None = None
    ) -> dict[str, dict[str, types.Tool]]:
        """
        Get tools from a specific server or all servers.

        Args:
            server_name (str | None): Name of the server to get tools from.
                                      If None, get tools from all servers.

        Returns:
            dict[str, dict[str, types.Tool]]: A dictionary of tools, where the keys are server names

        Raises:
            ValueError: If the server is not found or not connected.
        """
        if server_name and server_name not in self.config["mcpServers"]:
            raise ValueError(f"Server {server_name} not found in configuration")

        all_tools = {}
        for name, conn in self.connections.items():
            if server_name and name != server_name:
                continue
            tools = await conn.list_tools()
            for tool in tools:
                all_tools[f"{name}/{tool.name}"] = tool

        return all_tools

    async def get_servers(self) -> dict[str, Server]:
        """
        Get all configured servers.

        Returns:
            dict[str, Server]: A dictionary of server names and their corresponding Server objects.
        """
        return {name: conn.server for name, conn in self.connections.items()}

    async def aclose(self):
        """Close all server connections."""
        for conn in reversed(self.connections.values()):
            await conn.aclose()

        self.connections.clear()

    async def __aenter__(self):
        """
        Async context manager entry point. Initializes the router.

        Returns:
            Router: The initialized router instance.
        """
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """
        Async context manager exit point. Closes all server connections.
        """
        await self.aclose()


async def main():
    mcp_servers = DEFAULT_CONFIG
    async with Router(mcp_servers) as router:
        servers = await router.route_servers("github memory", 5)
        tools = await router.route_tools("git", 5)
        logger.info(servers)
        logger.info(tools)


if __name__ == "__main__":
    asyncio.run(main())
