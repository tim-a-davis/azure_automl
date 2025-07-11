#!/usr/bin/env python3
"""
Test client for our fastapi-mcp HTTP-based MCP server.
This attempts to properly connect to the SSE endpoint and interact with the MCP protocol.
"""

import asyncio
import json
from typing import Any, Dict, Optional

import httpx


class MCPHTTPClient:
    """HTTP-based MCP client for testing fastapi-mcp servers."""

    def __init__(self, base_url: str = "http://localhost:8005", token: str = None):
        self.base_url = base_url
        self.token = token
        self.session_id: Optional[str] = None
        self.http_client = httpx.AsyncClient()

    async def connect(self) -> bool:
        """Connect to the MCP server and get a session ID."""
        try:
            print(f"Attempting to connect to {self.base_url}/mcp")
            
            headers = {"Accept": "text/event-stream"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            # Connect to the SSE endpoint to get a session
            async with self.http_client.stream(
                "GET",
                f"{self.base_url}/mcp",
                headers=headers,
                timeout=10.0,
            ) as response:
                print(f"Response status: {response.status_code}")
                print(f"Response headers: {dict(response.headers)}")

                if response.status_code == 200:
                    print("Reading SSE stream...")
                    # Read the first few lines to get the session ID
                    line_count = 0
                    async for line in response.aiter_lines():
                        line_count += 1
                        print(f"Line {line_count}: {line}")

                        if line.startswith("data: "):
                            data = line[6:]  # Remove "data: " prefix
                            if "session_id=" in data:
                                # Extract session ID from the endpoint URL
                                self.session_id = data.split("session_id=")[1]
                                print(f"Connected with session ID: {self.session_id}")
                                return True

                        # Don't read forever
                        if line_count > 5:
                            break
                else:
                    print(f"Error response: {response.text}")

        except Exception as e:
            print(f"Connection failed: {e}")
            import traceback

            traceback.print_exc()

        return False

    async def send_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a JSON-RPC message to the MCP server."""
        if not self.session_id:
            print("Not connected - no session ID")
            return None

        try:
            endpoint = f"{self.base_url}/mcp/messages/"
            headers = {"Content-Type": "application/json"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
                
            response = await self.http_client.post(
                endpoint,
                params={"session_id": self.session_id},
                json=message,
                headers=headers,
                timeout=30.0,
            )

            print(f"Sent: {json.dumps(message, indent=2)}")
            print(f"Response status: {response.status_code}")
            print(f"Response: {response.text}")

            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error response: {response.text}")

        except Exception as e:
            print(f"Send failed: {e}")

        return None

    async def initialize(self) -> bool:
        """Initialize the MCP session."""
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }

        response = await self.send_message(init_message)
        return response is not None

    async def list_tools(self) -> Optional[Dict[str, Any]]:
        """List available tools."""
        message = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}

        return await self.send_message(message)

    async def call_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Call a specific tool."""
        message = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }

        return await self.send_message(message)

    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()


async def test_mcp_client():
    """Test the MCP client with our FastAPI server."""
    # Use the token we just generated
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXIiLCJ0aWQiOiJ0ZXN0LXRlbmFudCIsImlhdCI6MTc1MjIwOTE4OSwiZXhwIjoxNzUyMjk1NTg5fQ.hxOd4tA-goD5TcNGn72bSju31pM0uTz8V87hNV7fIp0"
    client = MCPHTTPClient(token=token)

    try:
        print("Testing MCP HTTP Client...")
        print("=" * 50)

        # Step 1: Connect
        print("\n1. Connecting to MCP server...")
        if not await client.connect():
            print("❌ Failed to connect")
            return
        print("✅ Connected successfully")

        # Step 2: Initialize
        print("\n2. Initializing session...")
        if not await client.initialize():
            print("❌ Failed to initialize")
            return
        print("✅ Session initialized")

        # Step 3: List tools
        print("\n3. Listing available tools...")
        tools_response = await client.list_tools()
        if tools_response:
            print("✅ Tools listed successfully")
            # Print the tools if available
            if "result" in tools_response and "tools" in tools_response["result"]:
                tools = tools_response["result"]["tools"]
                print(f"Found {len(tools)} tools:")
                for tool in tools:
                    print(
                        f"  - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}"
                    )
            else:
                print("No tools found in response")
        else:
            print("❌ Failed to list tools")

        # Step 4: Try calling a tool (if we found any)
        if tools_response and "result" in tools_response:
            tools = tools_response["result"].get("tools", [])
            if tools:
                print(f"\n4. Testing tool call with '{tools[0]['name']}'...")
                tool_result = await client.call_tool(tools[0]["name"], {})
                if tool_result:
                    print("✅ Tool call successful")
                    print(f"Result: {json.dumps(tool_result, indent=2)}")
                else:
                    print("❌ Tool call failed")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_mcp_client())
