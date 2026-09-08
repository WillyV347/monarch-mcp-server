"""Allow `python -m monarch_mcp_server` as a Codex-safe stdio launcher."""

from monarch_mcp_server.app import main

if __name__ == "__main__":
    main()
