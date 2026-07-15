"""Offline, synthetic entry point for the public portfolio project."""

from __future__ import annotations

import asyncio

from .demo import run_scripted_demo

def main() -> None:
    transcript = asyncio.run(run_scripted_demo())
    print("Sport-LM synthetic offline demo\n")
    for user_message, turn in transcript:
        print(f"User: {user_message}")
        if turn.tool_call:
            print(
                "Tool call: "
                f"{turn.tool_call['function']['name']}"
                f"({turn.tool_call['function']['arguments']})"
            )
        print(f"Agent: {turn.reply}\n")


if __name__ == "__main__":
    main()
