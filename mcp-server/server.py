import os

import httpx
from fastmcp import FastMCP

USER_SERVICE_URL = os.environ.get("USER_SERVICE_URL", "http://user-service:8001")
PORTFOLIO_SERVICE_URL = os.environ.get(
    "PORTFOLIO_SERVICE_URL", "http://portfolio-service:8002"
)

mcp = FastMCP("apira")


@mcp.tool()
async def login(username: str, password: str) -> dict:
    """Authenticate a user and return user_id."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{USER_SERVICE_URL}/login",
            json={"username": username, "password": password},
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_portfolio(user_id: int) -> dict:
    """Return portfolio holdings for a user_id."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{PORTFOLIO_SERVICE_URL}/portfolio",
            params={"user_id": user_id},
        )
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000,
        path="/mcp",
    )
