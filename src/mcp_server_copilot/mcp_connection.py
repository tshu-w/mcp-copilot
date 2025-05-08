import logging
from contextlib import AsyncExitStack
from typing import Any

import mcp.types as types
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import StdioServerParameters, stdio_client

from mcp_server_copilot.schemas import Server

logger = logging.getLogger(__name__)


class MCPConnection:
    """Manages MCP server and client connection."""

    def __init__(self, server: Server) -> None:
        self.server = server
        self._session: ClientSession | None = None
        self._exit_stack = AsyncExitStack()

    async def connect(self) -> None:
        """Establishes connection to the MCP server using STDIO or SSE."""
        try:
            if self.server.config.command:
                # STDIO connection
                server_params = StdioServerParameters(
                    **self.server.config.model_dump(include={"command", "args", "env"})
                )
                read, write = await self._exit_stack.enter_async_context(
                    stdio_client(server_params)
                )
                session = await self._exit_stack.enter_async_context(
                    ClientSession(read, write)
                )
                await session.initialize()
                self._session = session
            elif self.server.config.url:
                # SSE connection
                server_params = self.server.config.model_dump(
                    include={"url", "headers"}
                )
                read, write = await self._exit_stack.enter_async_context(
                    sse_client(**server_params)
                )
                session = await self._exit_stack.enter_async_context(
                    ClientSession(read, write)
                )
                await session.initialize()
                self._session = session

            list_tools_result = await self._session.list_tools()
            self.server.tools = list_tools_result.tools

            logger.info(f"Successfully connected to server: {self.server.name}")
        except Exception as e:
            logging.warning(f"Error initializing server {self.server.name}: {e}")
            await self.aclose()
            raise

    async def list_tools(self) -> list[types.Tool]:
        """Lists available tools from the MCP server."""
        if not self._session:
            raise RuntimeError(
                f"Server {self.server.name} not established. Call connect() first."
            )

        return self.server.tools

    async def call_tool(self, tool_name: str, params: dict) -> Any:
        """Calls a specific tool with given parameters."""
        if not self._session:
            raise RuntimeError(
                f"Server {self.server.name} not established. Call connect() first."
            )
        return await self._session.call_tool(tool_name, params)

    async def aclose(self) -> None:
        """Closes the connection."""
        try:
            await self._exit_stack.aclose()
            self._session = None
        except Exception as e:
            logging.warning(f"Error during cleanup of server {self.server.name}: {e}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Async context manager exit."""
        await self.aclose()
