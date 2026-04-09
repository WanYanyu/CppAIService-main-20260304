from typing import TypedDict, List, Dict, Any


class TutorGraphState(TypedDict, total=False):
    problem_id: str
    problem_description: str
    current_code: str
    test_case_results: str
    chat_history: List[Dict[str, str]]
    user_message: str

    planned_agents: List[str]
    next_agent_idx: int

    test_cases_text: str
    test_cases: List[Dict[str, str]]
    runtime_result: Dict[str, Any]
    complexity_result: str
    rag_result: str
    agent_statuses: Dict[str, str]
    token_usage: Dict[str, Dict[str, int]]

    tool_log: List[str]
    final_reply: str
