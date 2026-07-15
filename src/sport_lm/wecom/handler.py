from __future__ import annotations

import json
import logging
import random
import uuid
from typing import Any

from ..config import Config
from ..llm.base import BaseLLM
from ..prompts import get_system_prompt
from ..sop.parser import get_modify_scene_ids, load_scene_menu
from ..sop.router import select_scene_ids
from ..tools import TOOLS, run_tool
from ..user_map import UserMap
from ..security.input_filter import check_message
from ..security.privacy import pseudonymize
from ..utils.cache import UserCache
from ..utils.event_log import log_event
from .client import MessageChannelClient

THINKING_LIST = [
    "🤔 正在疯狂思考中…",
    "⚡ 大脑高速运转ing...",
    "✍️ 正在组织超棒的回答...",
    "💬 憋个好答案出来...",
    "🧩 正在梳理逻辑中...",
    "✨ 马上给你答案...",
]

SECURITY_REJECT_LIST = [
    "违规内容已屏蔽，相关记录已保存（真的）❌",
    "别搞小动作啦，已经记在系统里咯（真的）🤫",
    "危险想法已拦截，行为已悄悄记小本本上（真的）📝",
    "你这招我见多啦，已记录在案，别再试啦（真的）😼",
    "检测到违规尝试，已自动记录（真的）🔒",
]

FALLBACK_LIST = [
    "哎呀，好像出了点小状况😥，暂时没法给你准确回复啦，你可以换个问题再试试～",
    "抱歉抱歉，我这边有点小迷糊了🤯，没能理解你的意思，再描述清楚一点点吧！",
    "呜呜，刚才的思考好像卡住了😣，换个方式提问，我马上重新回答！",
    "抱歉呀，本次回复异常啦🥺，你可以再发一遍问题，我努力帮你解答～",
    "不好意思，暂时无法完成回复🙏，你可以简化问题或稍后再试～",
]

class MessageHandler:
    def __init__(
        self,
        client: MessageChannelClient,
        config: Config,
        user_map: UserMap,
        llm: BaseLLM,
        cache: UserCache,
    ) -> None:
        self._client = client
        self._config = config
        self._user_map = user_map
        self._llm = llm
        self._cache = cache
        self._logger = logging.getLogger(__name__)
        self._scene_menu = load_scene_menu(config.sop_file_path)
        self._sop_path = config.sop_file_path
        self._modify_scene_ids = get_modify_scene_ids(config.sop_file_path)

    def register(self) -> None:
        self._client.on("message.text", self.on_text)
        self._client.on("message.voice", self.on_voice)

    async def on_text(self, frame: dict[str, Any]) -> None:
        try:
            await self._handle_text(frame)
        except Exception as exc:
            self._logger.exception("message.text 处理失败: %s", exc)
            await self._client.reply_text(frame, "抱歉，系统暂时繁忙，请稍后再试。")

    async def on_voice(self, frame: dict[str, Any]) -> None:
        try:
            self._logger.info("=== 收到语音消息 ===")
            # 检查语音消息是否已经包含转写的文字
            voice_body = frame.get("body", {}).get("voice", {})
            content = voice_body.get("content", "") or voice_body.get("transcription", "") or voice_body.get("text", "")
            
            if content:
                # 如果已经有转写的文字，直接当作文本消息处理
                self._logger.info("语音已自动转写，length=%s", len(content))
                # 构造一个类似文本消息的frame
                text_frame = frame.copy()
                text_frame["body"]["text"] = {"content": content}
                await self._handle_text(text_frame)
            else:
                # 如果没有转写文字，告诉用户暂时不支持
                self._logger.warning("语音消息没有转写文字")
                await self._client.reply_text(frame, "抱歉，暂时无法处理语音消息，请发送文字消息。")
        except Exception as exc:
            self._logger.exception("message.voice 处理失败: %s", exc)
            await self._client.reply_text(frame, "抱歉，系统暂时繁忙，请稍后再试。")

    async def _handle_text(self, frame: dict[str, Any]) -> None:
        request_id = uuid.uuid4().hex
        content = frame["body"]["text"]["content"]
        filter_result = check_message(content)
        if not filter_result.allowed:
            wecom_id = frame.get("body", {}).get("from", {}).get("userid", "")
            raw_user_info = self._user_map.get_user_info(wecom_id)
            user_info = raw_user_info if isinstance(raw_user_info, dict) else {}
            subject_ref = pseudonymize(wecom_id)
            log_event(
                {
                    "level": "WARNING",
                    "type": "security_blocked",
                    "request_id": request_id,
                    "subject_ref": subject_ref,
                    "reason": filter_result.reason,
                    "text_length": len(content),
                }
            )
            logging.getLogger("security").warning(
                "input_blocked subject_ref=%s reason=%s length=%s",
                subject_ref,
                filter_result.reason,
                len(content),
            )
            await self._client.reply_text(frame, random.choice(SECURITY_REJECT_LIST))
            return
        wecom_id = (
            frame.get("body", {})
            .get("from", {})
            .get("userid", "")
        )
        self._logger.info("=== INCOMING MESSAGE ===")
        subject_ref = pseudonymize(wecom_id)
        self._logger.info(
            "incoming subject_ref=%s content_length=%s", subject_ref, len(content)
        )
        raw_user_info = self._user_map.get_user_info(wecom_id)
        user_info = raw_user_info if isinstance(raw_user_info, dict) else {}
        self._logger.info("identity_resolved subject_ref=%s found=%s", subject_ref, bool(user_info))
        log_event(
            {
                "level": "INFO",
                "type": "user_input",
                "request_id": request_id,
                "subject_ref": subject_ref,
                "text_length": len(content),
            }
        )
        if not (user_info.get("subject_id") or "").strip():
            template_reply = "抱歉，当前匿名主体不在此演示流程的办理范围内。"
            log_event(
                {
                    "level": "INFO",
                    "type": "user_out_of_scope",
                    "request_id": request_id,
                    "subject_ref": subject_ref,
                    "text_length": len(content),
                    "reply_length": len(template_reply),
                }
            )
            await self._client.reply_text(frame, template_reply)
            return
        user_facts = self._format_user_facts(wecom_id, user_info)
        thinking_text = random.choice(THINKING_LIST)
        stream_id = await self._client.reply_stream(
            frame, thinking_text, finish=False
        )
        log_event(
            {
                "level": "INFO",
                "type": "thinking_prompt",
                "request_id": request_id,
                "stream_id": stream_id,
                "subject_ref": subject_ref,
                "message_length": len(thinking_text),
            }
        )
        self._logger.info("user_facts prepared subject_ref=%s", subject_ref)
        system_prompt = get_system_prompt(self._scene_menu, user_facts)
        self._logger.info(
            "scene_menu_summary: count=%s preview=%s",
            len(self._scene_menu.split("；")) if self._scene_menu else 0,
            "；".join(self._scene_menu.split("；")[:3]) if self._scene_menu else "",
        )
        scene_ids = await select_scene_ids(
            self._llm, self._scene_menu, content, self._sop_path
        )
        self._logger.info("scene_ids=%s", scene_ids)
        log_event(
            {
                "level": "INFO",
                "type": "scene_ids",
                "request_id": request_id,
                "subject_ref": subject_ref,
                "scene_ids": scene_ids,
            }
        )
        history = await self._cache.get_recent_history(wecom_id, limit=8)
        last_assistant = next(
            (msg for msg in reversed(history) if msg.get("role") == "assistant"),
            None,
        )
        last_assistant_msg = (last_assistant or {}).get("content", "")
        if "确认" in content and self._is_project_selection_prompt(last_assistant_msg):
            scene_ids = ["场景1"]
            self._logger.warning("检测到项目确认意图，强制使用报名提交场景")
        if self._has_modify_intent(content):
            self._logger.warning("检测到修改意图，期望 LLM 调用 update_user_data")
            if not any(scene_id in self._modify_scene_ids for scene_id in scene_ids):
                if self._modify_scene_ids:
                    scene_ids.extend(self._modify_scene_ids)
                    self._logger.warning(
                        "已强制加入修改场景: %s", self._modify_scene_ids
                    )
                else:
                    self._logger.warning("未找到修改场景可加入")
        if last_assistant and self._is_project_selection_prompt(last_assistant.get("content", "")) and self._is_simple_confirm_or_number(content):
            self._logger.warning("检测到选项目后的确认/数字回复，强制加入修改/报名场景")
            if self._modify_scene_ids:
                for scene_id in self._modify_scene_ids:
                    if scene_id not in scene_ids:
                        scene_ids.append(scene_id)
        if len(scene_ids) > 5:
            self._logger.warning("scene_ids 超过 5 个，截断为前 3 个")
            scene_ids = scene_ids[:3]
        if self._has_signup_confirm_intent(content):
            if not any(scene_id == "场景1" or "报名" in scene_id for scene_id in scene_ids):
                scene_ids.insert(0, "场景1")
                self._logger.warning("检测到确认报名意图，强制加入场景1")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": user_facts},
        ]
        messages.extend(history)
        messages.append({"role": "user", "content": content})
        messages = [msg for msg in messages if msg is not None]

        # 先把场景选择结果转成工具调用，喂给模型
        if scene_ids:
            tool_calls = []
            for idx, scene_id in enumerate(scene_ids, start=1):
                tool_calls.append(
                    {
                        "id": f"call_scene_{idx}",
                        "type": "function",
                        "function": {
                            "name": "textfetch_scene_sop",
                            "arguments": json.dumps({"scene_id": scene_id}, ensure_ascii=False),
                        },
                    }
                )
            messages.append({"role": "assistant", "tool_calls": tool_calls})
            for call in tool_calls:
                self._logger.info(
                    "tool_call(pre): name=%s arguments_length=%s",
                    call["function"]["name"],
                    len(call["function"].get("arguments", "")),
                )
                tool_content = await run_tool(
                    call["function"]["name"],
                    call["function"].get("arguments", ""),
                    self._sop_path,
                    user_info,
                )
                log_event(
                    {
                        "level": "INFO",
                        "type": "tool_call",
                        "request_id": request_id,
                        "subject_ref": subject_ref,
                        "tool_name": call["function"]["name"],
                        "arguments_length": len(call["function"].get("arguments", "")),
                        "result_length": len(tool_content),
                    }
                )
                self._logger.info(
                    "tool_result(pre): name=%s summary=%s",
                    call["function"]["name"],
                    self._summarize_text(tool_content),
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "name": call["function"]["name"],
                        "content": tool_content,
                    }
                )

        try:
            reply = ""
            for _ in range(5):
                self._logger.info("=== LLM CALL ===")
                self._logger.info("messages_summary=%s", self._summarize_messages(messages))
                response = await self._llm.generate(messages, tools=TOOLS)
                self._logger.info(
                    "llm_response: content_len=%s has_tool_calls=%s",
                    len(response.content or ""),
                    bool(response.tool_calls),
                )
                log_event(
                    {
                        "level": "INFO",
                        "type": "llm_response",
                        "request_id": request_id,
                        "subject_ref": subject_ref,
                        "content_length": len(response.content or ""),
                        "tool_call_count": len(response.tool_calls or []),
                    }
                )
                if response.tool_calls:
                    messages.append(
                        {"role": "assistant", "tool_calls": response.tool_calls}
                    )
                    for call in response.tool_calls:
                        function = call.get("function", {})
                        tool_name = function.get("name", "")
                        arguments = function.get("arguments", "")
                        self._logger.info(
                            "tool_call: name=%s arguments_length=%s",
                            tool_name,
                            len(arguments),
                        )
                        tool_content = await run_tool(
                            tool_name,
                            arguments,
                            self._sop_path,
                            user_info,
                        )
                        log_event(
                            {
                                "level": "INFO",
                                "type": "tool_call",
                                "request_id": request_id,
                                "subject_ref": subject_ref,
                                "tool_name": tool_name,
                                "arguments_length": len(arguments),
                                "result_length": len(tool_content),
                            }
                        )
                        self._logger.info(
                            "tool_result: name=%s summary=%s",
                            tool_name,
                            self._summarize_text(tool_content),
                        )
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": call.get("id", ""),
                                "name": tool_name,
                                "content": tool_content,
                            }
                        )
                    continue

                reply = response.content or ""
                self._logger.info("final_reply_length=%s", len(reply))
                break
            if not reply:
                reply = random.choice(FALLBACK_LIST)
        except Exception as exc:
            self._logger.exception("LLM 调用失败: %s", exc)
            reply = random.choice(FALLBACK_LIST)

        log_event(
            {
                "level": "INFO",
                "type": "final_reply",
                "request_id": request_id,
                "stream_id": stream_id,
                "subject_ref": subject_ref,
                "reply_length": len(reply),
            }
        )
        await self._client.reply_stream(frame, reply, finish=True, stream_id=stream_id)
        await self._cache.add_message(wecom_id, "user", content)
        await self._cache.add_message(wecom_id, "assistant", reply)

    @staticmethod
    def _format_user_facts(wecom_id: str, user_info: dict[str, Any]) -> str:
        lines = [
            "当前办理人事实：",
            f"通道匿名引用: {pseudonymize(wecom_id)}",
            f"业务主体: {user_info.get('subject_id') or '未知'}",
            f"显示名称: {user_info.get('display_name') or '匿名用户'}",
            f"示例分组: {user_info.get('group') or '未知'}",
            f"示例类别: {user_info.get('category') or '未知'}",
            "（需要查询状态时必须使用工具，不要凭空回答）",
        ]
        return "\n".join(lines)


    @staticmethod
    def _summarize_messages(messages: list[dict[str, Any]]) -> str:
        parts = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            content_len = len(content) if isinstance(content, str) else 0
            parts.append(f"{role}(len={content_len})")
        return " | ".join(parts)

    @staticmethod
    def _summarize_text(text: str, limit: int = 200) -> str:
        if not text:
            return ""
        text = text.replace("\n", " ").strip()
        return text if len(text) <= limit else text[:limit] + "..."

    @staticmethod
    def _has_modify_intent(content: str) -> bool:
        keywords = ["修改", "换成", "增加", "替换", "确认", "删除", "改成", "新增"]
        return any(keyword in content for keyword in keywords)

    @staticmethod
    def _is_project_selection_prompt(text: str) -> bool:
        keywords = ["请选择项目", "从下面选出", "编号", "最多 5 项", "直接回复编号"]
        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _is_simple_confirm_or_number(text: str) -> bool:
        content = text.strip()
        if content in ("确认", "好的", "是的"):
            return True
        # 纯数字或数字组合（允许空格/逗号分隔）
        normalized = content.replace(" ", "").replace(",", "")
        return normalized.isdigit()

    @staticmethod
    def _has_signup_confirm_intent(text: str) -> bool:
        keywords = ["确认报名", "确认", "好的", "开始报名", "我要报名"]
        return any(keyword in text for keyword in keywords)
