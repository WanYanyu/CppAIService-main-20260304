import os
import json
import logging
from openai import AsyncOpenAI
from models import TutorChatRequest, TutorChatResponse

# ─── 加载环境变量 ──────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# ─── DeepSeek 客户端初始化 ─────────────────────────────────────
api_key  = os.getenv("DEEPSEEK_API_KEY", "")
base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
MODEL    = "deepseek-chat"

client = AsyncOpenAI(api_key=api_key, base_url=base_url)

# ─── 苏格拉底导师系统提示词 ────────────────────────────────────
TUTOR_SYSTEM_PROMPT = """你是一位苏格拉底式的 C++ 编程导师，你的使命是通过提问和引导帮助学生独立发现问题，而不是直接给出答案。

你有以下四个工具可以调用：
1. run_sandbox_code     — 将学生代码送入沙盒实际运行，获取真实 stdout/stderr
2. web_search           — 搜索 C++ 文档、编译器报错含义、STL 函数签名
3. analyze_complexity   — 分析代码的时间/空间复杂度（适合 TLE 场景）
4. get_similar_hint     — 根据题型给出算法方向的苏格拉底式提示（不给答案）

工作流程：
- 当学生提交代码后，先考虑是否需要调用 run_sandbox_code 来获取真实执行结果。
- 如果执行结果中含有编译错误，分析错误原因，然后再提问引导学生。
- 如果是 TLE（超时），调用 analyze_complexity 工具分析瓶颈。
- 如果学生完全没思路，调用 get_similar_hint 给出算法模式提示。
- 综合所有工具返回的信息，组织苏格拉底式的最终回复。

回复规则（非常重要）：
- **绝对禁止**直接给出完整的修复代码。
- **防止幻觉与过度批评**：如果经过沙盒运行和逻辑分析，发现代码完全能跑通且没有逻辑漏洞，请**强烈表扬**学生！绝对禁止去捏造不存在的语法错误（如认为 `a ? b : c` 是错的）或无中生有地挑剔等价的正确逻辑。
- 用提问的方式引导（仅当代码真的有错时），例如："你觉得当 n=0 时，第 5 行的循环会发生什么？"
- 可以指出明确的语法错误，但不要直接改掉，而是问"你注意到这里的写法和标准用法有什么差异吗？"
- 保持对话简短、友好、鼓励性。
"""

# ─── Function Calling 工具定义（OpenAI 格式）─────────────────
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "run_sandbox_code",
            "description": "将完整的 C++ 代码提交到安全沙盒编译并执行，返回真实的 stdout/stderr。用于验证代码能否编译、特定输入的实际输出，或复现某个 Bug。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "完整的 C++ 代码字符串，必须包含 main 函数。"
                    },
                    "test_input": {
                        "type": "string",
                        "description": "可选，标准输入（stdin），用于 scanf/cin 读取。"
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "在网上搜索 C++ 文档、编译器报错含义或标准库用法。适合用于不熟悉的 C++17/20 特性、冷门报错信息或需要核实 STL 函数签名时。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索词，例如 'std::vector erase iterator invalidation c++'"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_complexity",
            "description": "分析 C++ 代码的时间复杂度和空间复杂度，识别性能瓶颈。适合代码逻辑正确但 TLE 的场景。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "要分析的完整 C++ 代码。"
                    },
                    "problem_description": {
                        "type": "string",
                        "description": "可选，题目描述，帮助判断数据规模约束。"
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_similar_hint",
            "description": "根据题目类型和当前错误，给出苏格拉底式的算法方向提示（不给答案）。适合学生完全没头绪或多次 Wrong Answer 后需要方向引导时。",
            "parameters": {
                "type": "object",
                "properties": {
                    "problem_description": {
                        "type": "string",
                        "description": "题目描述内容。"
                    },
                    "error_type": {
                        "type": "string",
                        "description": "可选，当前的错误类型（如 'Wrong Answer', 'TLE', '无从下手'）。"
                    }
                },
                "required": ["problem_description"]
            }
        }
    }
]

# ─── 工具分发器（负责实际调用 agent_tools 里的函数）─────────────
async def _dispatch_tool(tool_name: str, tool_args: dict) -> str:
    """根据 LLM 返回的 tool_name 调用对应工具函数"""
    from agent_tools import (
        run_sandbox_code,
        web_search,
        analyze_complexity,
        get_similar_hint,
    )
    try:
        if tool_name == "run_sandbox_code":
            return await run_sandbox_code.ainvoke(tool_args)
        elif tool_name == "web_search":
            return await web_search.ainvoke(tool_args)
        elif tool_name == "analyze_complexity":
            return await analyze_complexity.ainvoke(tool_args)
        elif tool_name == "get_similar_hint":
            return await get_similar_hint.ainvoke(tool_args)
        else:
            return f"[错误] 未知工具：{tool_name}"
    except Exception as e:
        logger.error(f"Tool '{tool_name}' failed: {e}", exc_info=True)
        return f"[工具执行失败] {tool_name}：{str(e)}"


# ─── 主处理函数（Function Calling 循环）────────────────────────
async def process_tutor_request(request: TutorChatRequest) -> TutorChatResponse:
    """
    使用 OpenAI Function Calling 模式驱动苏格拉底导师 Agent。

    循环逻辑：
    1. LLM 决定是否调用工具（tool_calls 非空）
    2. 如果有工具调用 → 执行工具 → 把结果追加到 messages → 再次调用 LLM
    3. LLM 输出纯文本（finish_reason == 'stop'）→ 返回给用户
    """
    # 构建初始 messages
    messages = [
        {"role": "system", "content": TUTOR_SYSTEM_PROMPT},
        {
            "role": "system",
            "content": (
                f"--- 当前题目上下文 ---\n{request.problem_description}\n"
                f"--- 学生当前的代码 ---\n{request.current_code}"
            )
        }
    ]

    # 注入历史对话
    for msg in request.chat_history:
        if msg.role in ("user", "assistant"):
            messages.append({"role": msg.role, "content": msg.content})

    # 注入当前用户消息
    user_msg = request.user_message.strip() or "我的代码哪里有问题？"

    # 强行把当前代码拼在最后一条消息末尾，防止多轮对话后 LLM 选择性遗忘 system prompt 里的代码
    if request.current_code:
        user_msg += f"\n\n[附：学生当前编辑器里的代码]\n```cpp\n{request.current_code}\n```"

    if request.test_case_results:
        user_msg += f"\n\n[附：沙箱运行结果]\n{request.test_case_results}"

    messages.append({"role": "user", "content": user_msg})

    tool_chain_log = []
    MAX_ITERATIONS = 5  # 防止无限工具调用循环

    for iteration in range(MAX_ITERATIONS):
        logger.info(f"[TutorAgent] Function Calling 第 {iteration + 1} 轮")

        response = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto",      # LLM 自主决定是否调用工具
            temperature=0.4,
        )

        choice = response.choices[0]
        finish_reason = choice.finish_reason
        message = choice.message

        # 将 LLM 的回复追加到消息链
        messages.append(message.model_dump(exclude_unset=True))

        # 情况1：LLM 直接返回最终文本
        if finish_reason == "stop":
            reply = message.content or "（导师没有返回任何内容）"
            logger.info(f"[TutorAgent] 完成，共调用工具 {len(tool_chain_log)} 次")
            return TutorChatResponse(
                reply=reply,
                error_analysis="\n".join(tool_chain_log) if tool_chain_log else "无工具调用"
            )

        # 情况2：LLM 要调用工具
        if finish_reason == "tool_calls" and message.tool_calls:
            for tool_call in message.tool_calls:
                fn_name = tool_call.function.name
                fn_args_raw = tool_call.function.arguments
                try:
                    fn_args = json.loads(fn_args_raw)
                except Exception:
                    fn_args = {}

                logger.info(f"[TutorAgent] 调用工具: {fn_name}({fn_args})")
                tool_chain_log.append(f">> Tool: {fn_name}({list(fn_args.keys())})")

                tool_result = await _dispatch_tool(fn_name, fn_args)

                # 把工具返回值追加到 messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": fn_name,
                    "content": tool_result
                })
        else:
            # 意外情况：finish_reason 不是 stop 也不是 tool_calls
            break

    # 超过最大迭代次数，返回兜底答复
    logger.warning("[TutorAgent] 已达到最大工具调用次数，返回兜底回复")
    return TutorChatResponse(
        reply="导师处理时间过长，请换一种方式提问，或者直接描述你遇到的具体报错信息。",
        error_analysis="Max iterations reached"
    )
