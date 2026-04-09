import json
import asyncio
from typing import Literal

from langgraph.graph import StateGraph, END
from openai import AsyncOpenAI

from .config import settings
from .state import TutorGraphState
from .agents.runtime_agent import run_code_agent
from .agents.testcase_agent import run_testcase_agent_with_meta, format_test_cases_as_text
from .agents.complexity_agent import run_complexity_agent
from .agents.syntax_rag_agent import run_syntax_rag_agent

try:
    from langsmith import traceable
except Exception:
    def traceable(*args, **kwargs):
        def _decorator(fn):
            return fn
        return _decorator


def _set_agent_status(state: TutorGraphState, agent: str, status: str) -> None:
    statuses = state.setdefault("agent_statuses", {})
    statuses[agent] = status


def _add_token_usage(state: TutorGraphState, name: str, usage: dict) -> None:
    usage = usage or {}
    current = state.setdefault("token_usage", {})
    current[name] = {
        "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
        "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
        "total_tokens": int(usage.get("total_tokens", 0) or 0),
    }


def _token_summary_text(state: TutorGraphState) -> str:
    usage_map = state.get("token_usage", {}) or {}
    if not usage_map:
        return ""

    total_prompt = 0
    total_completion = 0
    total_tokens = 0
    lines = []
    for name, usage in usage_map.items():
        p = int(usage.get("prompt_tokens", 0) or 0)
        c = int(usage.get("completion_tokens", 0) or 0)
        t = int(usage.get("total_tokens", 0) or 0)
        total_prompt += p
        total_completion += c
        total_tokens += t
        lines.append(f"- {name}: prompt={p}, completion={c}, total={t}")

    lines.append(f"- total: prompt={total_prompt}, completion={total_completion}, total={total_tokens}")
    return "Token 使用统计：\n" + "\n".join(lines)


@traceable(name="tutor2.supervisor", run_type="chain")
async def supervisor_node(state: TutorGraphState) -> TutorGraphState:
    _set_agent_status(state, "supervisor", "running")
    user_message = state.get("user_message", "")
    code = state.get("current_code", "")
    desc = state.get("problem_description", "")

    planned = ["testcase", "runtime"]

    if settings.llm_api_key:
        client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
        prompt = (
            "你是多Agent调度器。可选agent: testcase,runtime,complexity,syntax_rag。"
            "根据用户消息、题目描述和代码，返回 JSON 数组，示例：[\"testcase\",\"runtime\",\"complexity\"]。"
            "规则：必须至少包含 runtime；如果语法概念不确定则加入 syntax_rag。"
            f"\n用户消息:\n{user_message}\n题目:\n{desc[:600]}\n代码:\n{code[:1200]}"
        )
        try:
            resp = await asyncio.wait_for(
                client.chat.completions.create(
                    model=settings.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                ),
                timeout=8,
            )
            usage = getattr(resp, "usage", None)
            _add_token_usage(
                state,
                "supervisor_planner",
                {
                    "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
                    "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
                    "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
                },
            )
            arr = json.loads(resp.choices[0].message.content)
            if isinstance(arr, list):
                planned = [x for x in arr if x in {"testcase", "runtime", "complexity", "syntax_rag"}]
        except Exception:
            pass

    msg = user_message.lower()
    if "语法" in user_message or "stl" in msg or "template" in msg:
        if "syntax_rag" not in planned:
            planned.append("syntax_rag")

    if "complexity" in msg or "复杂度" in user_message or "tle" in msg:
        if "complexity" not in planned:
            planned.append("complexity")

    if "runtime" not in planned:
        planned.insert(0, "runtime")

    state["planned_agents"] = planned
    state["next_agent_idx"] = 0
    state.setdefault("tool_log", []).append(f"supervisor planned: {planned}")
    _set_agent_status(state, "supervisor", "ok")
    return state


@traceable(name="tutor2.testcase", run_type="tool")
async def testcase_node(state: TutorGraphState) -> TutorGraphState:
    _set_agent_status(state, "testcase", "running")
    problem_id = state.get("problem_id", "0")
    problem_description = state.get("problem_description", "")
    parsed_cases, meta = await run_testcase_agent_with_meta(problem_id, problem_description)
    test_cases_text = format_test_cases_as_text(parsed_cases)

    state["test_cases_text"] = test_cases_text
    state["test_cases"] = parsed_cases
    _add_token_usage(state, "testcase_generation", meta.get("token_usage", {}))
    state.setdefault("tool_log", []).append(
        f"testcase fetched: {len(parsed_cases)} (source={meta.get('source', 'unknown')})"
    )
    state["next_agent_idx"] = state.get("next_agent_idx", 0) + 1
    _set_agent_status(state, "testcase", "ok")
    return state


@traceable(name="tutor2.runtime", run_type="tool")
async def runtime_node(state: TutorGraphState) -> TutorGraphState:
    _set_agent_status(state, "runtime", "running")
    result = await run_code_agent(state.get("current_code", ""), state.get("test_cases", []))
    state["runtime_result"] = result
    state.setdefault("tool_log", []).append(f"runtime status: {result.get('status', 'Unknown')}")
    state["next_agent_idx"] = state.get("next_agent_idx", 0) + 1
    _set_agent_status(state, "runtime", "ok")
    return state


@traceable(name="tutor2.complexity", run_type="tool")
async def complexity_node(state: TutorGraphState) -> TutorGraphState:
    _set_agent_status(state, "complexity", "running")
    runtime_status = (state.get("runtime_result") or {}).get("status", "")
    if runtime_status in {"Passed", "Unverified"}:
        analysis = await run_complexity_agent(state.get("current_code", ""), state.get("problem_description", ""))
        state["complexity_result"] = analysis.get("text", "")
        _add_token_usage(state, "complexity_analysis", analysis.get("token_usage", {}))
    else:
        state["complexity_result"] = "未触发复杂度分析（代码未通过运行阶段）。"
    state.setdefault("tool_log", []).append("complexity done")
    state["next_agent_idx"] = state.get("next_agent_idx", 0) + 1
    _set_agent_status(state, "complexity", "ok")
    return state


@traceable(name="tutor2.syntax_rag", run_type="tool")
async def syntax_rag_node(state: TutorGraphState) -> TutorGraphState:
    _set_agent_status(state, "syntax_rag", "running")
    rag_text = await run_syntax_rag_agent(state.get("user_message", ""), state.get("current_code", ""))
    state["rag_result"] = rag_text
    state.setdefault("tool_log", []).append("syntax_rag done")
    state["next_agent_idx"] = state.get("next_agent_idx", 0) + 1
    _set_agent_status(state, "syntax_rag", "ok")
    return state


@traceable(name="tutor2.composer", run_type="chain")
async def composer_node(state: TutorGraphState) -> TutorGraphState:
    _set_agent_status(state, "composer", "running")
    runtime = state.get("runtime_result", {})
    lines = []

    status = runtime.get("status")
    if status:
        lines.append(f"我先帮你真实运行了代码，当前状态是：{status}。")

    if status == "Unverified":
        lines.append("当前结果仅表示“代码可编译并运行”，并不代表题目答案正确；需要有效 expected_output 才能判题通过。")

    ai_feedback = runtime.get("ai_feedback")
    if ai_feedback:
        lines.append(f"运行反馈：{ai_feedback}")

    if state.get("complexity_result"):
        lines.append("复杂度分析：" + state["complexity_result"])

    if state.get("rag_result"):
        lines.append("语法检索：" + state["rag_result"])

    if state.get("test_cases_text"):
        lines.append("已生成并用于沙盒测试的样例：\n" + state["test_cases_text"])

    _set_agent_status(state, "composer", "ok")

    if state.get("agent_statuses"):
        status_text = "Agent 运行状态：\n" + "\n".join(
            [f"- {k}: {v}" for k, v in state.get("agent_statuses", {}).items()]
        )
        lines.append(status_text)

    token_text = _token_summary_text(state)
    if token_text:
        lines.append(token_text)

    if not lines:
        lines.append("我已经完成分析，但暂时没有可用结果，请重试一次。")

    lines.append("你希望我下一步优先看：边界样例、复杂度，还是语法细节？")
    state["final_reply"] = "\n\n".join(lines)
    return state


def _route_next(state: TutorGraphState) -> Literal["testcase", "runtime", "complexity", "syntax_rag", "composer"]:
    planned = state.get("planned_agents", [])
    idx = state.get("next_agent_idx", 0)
    if idx >= len(planned):
        return "composer"
    return planned[idx]


def build_graph():
    graph = StateGraph(TutorGraphState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("testcase", testcase_node)
    graph.add_node("runtime", runtime_node)
    graph.add_node("complexity", complexity_node)
    graph.add_node("syntax_rag", syntax_rag_node)
    graph.add_node("composer", composer_node)

    graph.set_entry_point("supervisor")
    graph.add_conditional_edges("supervisor", _route_next)
    graph.add_conditional_edges("testcase", _route_next)
    graph.add_conditional_edges("runtime", _route_next)
    graph.add_conditional_edges("complexity", _route_next)
    graph.add_conditional_edges("syntax_rag", _route_next)
    graph.add_edge("composer", END)

    return graph.compile()
