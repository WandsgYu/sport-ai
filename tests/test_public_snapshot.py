from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import tempfile
import unittest

from src.sport_lm.api.sports import query_user_info, update_user_data
from src.sport_lm.api.mock import SyntheticSportsAdapter
from src.sport_lm.demo import SyntheticAgentSession, run_scripted_demo
from src.sport_lm.main import main
from src.sport_lm.security.privacy import pseudonymize, redact_text, sanitize
from src.sport_lm.tools import run_tool
from src.sport_lm.utils.event_log import log_event


class PublicSnapshotTests(unittest.TestCase):
    def test_legacy_adapter_is_disabled(self) -> None:
        query = asyncio.run(query_user_info("subject-demo-001"))
        update = asyncio.run(
            update_user_data(
                {"subject_id": "subject-demo-001", "selected_items": []}
            )
        )
        self.assertEqual(query["ErrCode"], 503)
        self.assertEqual(update["ErrCode"], 503)
        self.assertIsNone(query["data"])

    def test_cross_subject_tool_access_is_rejected(self) -> None:
        result = asyncio.run(
            run_tool(
                "query_user_info",
                json.dumps({"subject_id": "subject-demo-002"}),
                "missing.md",
                {"subject_id": "subject-demo-001"},
            )
        )
        self.assertEqual(json.loads(result)["ErrCode"], 403)

    def test_redaction_covers_common_sensitive_values(self) -> None:
        phone = "138" + "0013" + "8000"
        email = "demo" + "@" + "example.invalid"
        ip_address = ".".join(["203", "0", "113", "10"])
        identity_number = "110101" + "19900101" + "1234"
        sample_url = "https" + "://" + "internal.invalid/a"
        raw = (
            f"phone {phone} email {email} ip {ip_address} "
            f"id {identity_number} token=do-not-log url {sample_url}"
        )
        redacted = redact_text(raw)
        for value in (
            phone,
            email,
            ip_address,
            identity_number,
            "do-not-log",
            sample_url,
        ):
            self.assertNotIn(value, redacted)

    def test_recursive_sanitizer_removes_private_keys(self) -> None:
        payload = sanitize(
            {
                "type": "tool_call",
                "arguments": {"phone": "synthetic-private-value"},
                "nested": {"secret": "private-value"},
            }
        )
        self.assertEqual(payload["arguments"], "[REDACTED]")
        self.assertEqual(payload["nested"]["secret"], "[REDACTED]")

    def test_event_log_never_persists_raw_private_content(self) -> None:
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            try:
                log_event(
                    {
                        "type": "user_input",
                        "request_id": "request-demo",
                        "subject_ref": pseudonymize("channel-user-demo"),
                        "text": "synthetic-private-message",
                        "result": {"secret": "private-value"},
                    }
                )
                stored = Path("logs/events.jsonl").read_text(encoding="utf-8")
            finally:
                os.chdir(original_cwd)
        self.assertNotIn("synthetic-private-message", stored)
        self.assertNotIn("private-value", stored)

    def test_synthetic_success_path_completes(self) -> None:
        transcript = asyncio.run(run_scripted_demo())
        final_turn = transcript[-1][1]
        self.assertEqual(final_turn.tool_result["ErrCode"], 0)
        self.assertEqual(
            final_turn.tool_result["data"]["operation_id"],
            "synthetic-enrollment-001",
        )

    def test_confirmation_requires_parameters(self) -> None:
        session = SyntheticAgentSession(SyntheticSportsAdapter())
        turn = asyncio.run(session.handle("确认提交"))
        self.assertIsNone(turn.tool_call)
        self.assertIn("尚未选择", turn.reply)

    def test_state_change_requires_confirmation(self) -> None:
        adapter = SyntheticSportsAdapter()
        session = SyntheticAgentSession(adapter)
        turn = asyncio.run(session.handle("我要报名示例项目B"))
        self.assertIsNone(turn.tool_call)
        self.assertEqual(adapter.write_count, 0)

    def test_idempotent_confirmation_does_not_repeat_write(self) -> None:
        adapter = SyntheticSportsAdapter()
        session = SyntheticAgentSession(adapter)
        asyncio.run(session.handle("我要报名示例项目C"))
        first = asyncio.run(session.handle("确认提交"))
        second = asyncio.run(session.handle("确认提交"))
        self.assertEqual(adapter.write_count, 1)
        self.assertEqual(
            first.tool_result["data"]["operation_id"],
            second.tool_result["data"]["operation_id"],
        )
        self.assertTrue(second.tool_result["idempotent_replay"])

    def test_demo_events_do_not_store_raw_messages(self) -> None:
        session = SyntheticAgentSession(SyntheticSportsAdapter())
        asyncio.run(session.handle("我要报名示例项目D"))
        serialized = json.dumps(session.events, ensure_ascii=False)
        self.assertNotIn("我要报名", serialized)

    def test_public_entry_point_runs_successfully(self) -> None:
        main()


if __name__ == "__main__":
    unittest.main()
