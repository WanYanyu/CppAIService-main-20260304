from typing import Dict, Any

from .graph import build_graph

_graph = build_graph()


async def process_tutor_request_v2(request) -> Dict[str, Any]:
    init_state = {
        "problem_id": request.problem_id,
        "problem_description": request.problem_description,
        "current_code": request.current_code,
        "test_case_results": request.test_case_results or "",
        "chat_history": [m.model_dump() for m in request.chat_history],
        "user_message": request.user_message or "我的代码哪里有问题？",
        "tool_log": [],
    }

    result = await _graph.ainvoke(init_state)
    return {
        "reply": result.get("final_reply", "导师暂时没有返回内容。"),
        "error_analysis": "\n".join(result.get("tool_log", [])) or "无",
    }
