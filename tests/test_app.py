"""Tests for the FastMCP app entry point."""

from unittest.mock import patch

from monarch_mcp_server.app import main


def test_main_runs_stdio_transport():
    with patch("monarch_mcp_server.app.mcp.run") as run:
        main()
    run.assert_called_once_with(transport="stdio")
