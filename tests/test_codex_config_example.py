"""Guard the Codex example so mutating tools stay on prompt, not auto-allow."""

from pathlib import Path
import tomllib

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "codex.config.toml"

WRITE_TOOLS = (
    "create_transaction",
    "update_transaction",
    "delete_transaction",
    "bulk_categorize_transactions",
    "upload_account_balance_history",
    "set_transaction_tags",
    "create_transaction_rule",
    "update_transaction_rule",
    "delete_transaction_rule",
    "split_transaction",
    "set_budget_amount",
    "update_merchant",
    "review_recurring_stream",
)


def test_codex_example_prompts_for_mutating_tools() -> None:
    config = tomllib.loads(EXAMPLE.read_text())
    server = config["mcp_servers"]["monarch-money"]

    assert server["default_tools_approval_mode"] == "prompt"

    tools = server["tools"]
    for name in WRITE_TOOLS:
        assert name in tools, f"{name} missing from Codex example"
        assert tools[name]["approval_mode"] == "prompt", (
            f"{name} must use prompt (Codex approve auto-allows the tool)"
        )

    for name, spec in tools.items():
        assert spec.get("approval_mode") != "approve", (
            f"{name} uses approval_mode=approve, which auto-allows the tool in Codex"
        )
