from backend.schemas.agent_schema import AgentState


def notion_node(state: AgentState) -> AgentState:
    summary = state.get("summary", "")
    tasks = state.get("tasks", [])
    room_id = state.get("room_id", "")

    # TODO: Notion API 연동 로직 (notion 모듈 완성 후 연결)
    # 지금은 임시 결과 반환
    notion_result = {
        "status": "skipped",
        "notion_url": None,
        "error": None,
    }

    return {
        **state,
        "notion_result": notion_result,
    }