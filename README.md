# MCP Server Copilot

[![python](https://img.shields.io/badge/-Python_3.10_%7C_3.11_%7C_3.12-blue?logo=python&logoColor=white&style=flat-square)](https://github.com/tshu-w/lightning-template)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json&style=flat-square)](https://github.com/astral-sh/ruff)

A Meta Model Context Protocol (MCP) server that seamlessly scales LLMs to 1000+ MCP servers through automatic routing without expose all servers and tools to LLMs directly.

<p align="center">
  <img src="https://github.com/user-attachments/assets/1ba57685-f06e-4cca-b696-ecaba7e6c7e9" alt="mcp_copilot" style="max-width:100%; height:auto; width:500px;">
</p>

## Components

### Tools

- `router-servers`: Route user query to appropriate servers. Use this when you need to find suitable servers that can handle the user's query. This should be your first step when processing a new query to determine which specialized servers are most relevant.
  - `query` (string, required): User's query to find relevant servers.
  - `top_k` (integer, optional): Maximum number of servers to return (default: 5).

- `route-tools`: Route user query to appropriate tools across all servers. Use this when you need to find specific tools that can address the user's request, regardless of which server hosts them. This is helpful when you know the task type but not which server handles it.
  - `query` (string, required): User's query to find relevant tools.
  - `top_k` (integer, optional): Maximum number of tools to return (default: 5).

- `execute-tool`: Execute a specific tool on a specific server based on previous routing results. Use this after you've identified the appropriate server and tool using the routing tools. This actually performs the requested operation.
  - `server_name` (string, required): Name of the server hosting the tool.
  - `tool_name` (string, required): Name of the tool to execute.
  - `params` (object, optional): Parameters to pass to the tool, as a key-value dictionary (default: null or empty object).

## Installation

### Using uv (recommended)

When using [`uv`](https://docs.astral.sh/uv/) no specific installation is needed. We will
use [`uvx`](https://docs.astral.sh/uv/guides/tools/) to directly run *mcp-server-copilot*.

### Using PIP

Alternatively you can install `mcp-server-copilot` via pip:

```
pip install mcp-server-copilot
```

After installation, you can run it as a script using:

```
python -m mcp_server_copilot
```

## Configuration

Copy `config/config.sample.json` to `~/.config/mcp-server-copilot`

Add to your MCP Client settings:

<details>
<summary>Using uvx</summary>

```json
"mcpServers": {
  "copilot": {
    "command": "uvx",
    "args": ["mcp-server-copilot", "--config", "~/.config/mcp-server-copilot/config.json"]
  }
}
```
</details>

<details>
<summary>Using pip installation</summary>

```json
"mcpServers": {
  "copilot": {
    "command": "python",
    "args": ["-m", "mcp_server_copilot", "--config", "~/.config/mcp-server-copilot/config.json"]
  }
}
```
</details>

## TODOs

- [ ] Manage Servers more easily
- [ ] Add Semantic Routing
- [ ] Add Planning Capabilities
