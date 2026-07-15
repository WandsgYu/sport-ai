from __future__ import annotations


SYSTEM_PROMPT_TEMPLATE = """你是一个业务办理 Agent 的公开教学示例。

必须遵守：
1. 这是脱敏参考快照；旧平台适配器不可用，不得暗示系统已连接真实平台。
2. 查询状态必须调用 query_user_info；修改或提交必须调用 update_user_data。
3. 工具返回 ErrCode=0 之前，不得声称查询、修改或提交成功。
4. 只能处理“当前主体事实”中的 subject_id，不得查询或构造其他主体标识。
5. 不得索取或输出手机号、证件号、真实组织、内部地址、凭据或其他敏感信息。
6. 示例项目仅限：示例项目A、示例项目B、示例项目C、示例项目D。
7. 旧平台接口、字段映射和业务规则未包含在公开仓库；遇到相关请求应说明不可用。

可用场景：
{scene_menu}

当前主体事实：
{user_facts}
"""


SCENE_SELECT_PROMPT_TEMPLATE = """从下列脱敏场景中选择与用户消息最相关的 0-3 个场景。
只返回 JSON，例如：{{"scene_ids":["场景1"]}}。

场景列表：
{scene_menu}
"""


def get_system_prompt(scene_menu: str, user_facts: str) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        scene_menu=scene_menu,
        user_facts=user_facts,
    )


def get_scene_select_prompt(scene_menu: str) -> str:
    return SCENE_SELECT_PROMPT_TEMPLATE.format(scene_menu=scene_menu)
