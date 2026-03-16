import httpx
import json
import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# =========================================================
# 工具1: run_sandbox_code  — 将用户代码送入物理沙盒编译执行
# =========================================================
SANDBOX_API_URL = "http://127.0.0.1:8002/api/sandbox/evaluate"

@tool
async def run_sandbox_code(code: str, test_input: str = "") -> str:
    """
    将一段 C++ 代码提交到安全沙盒中编译并执行，返回真实的 stdout / stderr。

    当你需要验证以下情况时调用此工具：
    - 用户的代码能否通过编译
    - 代码对特定输入会产生什么输出
    - 通过边界用例来验证某个具体 Bug 是否存在

    Args:
        code: 完整的 C++ 代码字符串，必须包含 main 函数。
        test_input: 可选，标准输入（stdin），用于 scanf/cin 读取。

    Returns:
        包含编译状态、stdout、stderr 的格式化报告字符串。
    """
    try:
        # ✅ FIXED: SandboxAgent EvaluationRequest 要求 test_cases 是对象列表
        # 且 expected_output 是必填字段，不能省略，传空字符串表示不校验输出
        payload = {
            "language": "cpp",
            "code": code,
            "test_cases": [
                {"input": test_input, "expected_output": ""}
            ]
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(SANDBOX_API_URL, json=payload)
            response.raise_for_status()
            result = response.json()

        # ✅ FIXED: EvaluationResult 的字段名是 stdout_log / stderr_log（不是 stdout/stderr）
        output = f"[沙箱执行结果]\n整体状态: {result.get('status', 'Unknown')}\n"

        stderr = result.get('stderr_log', '')
        stdout = result.get('stdout_log', '')
        ai_fb  = result.get('ai_feedback', '')

        if stderr:
            output += f"\n[编译/运行错误 (stderr)]\n{stderr}\n"
        if stdout:
            output += f"\n[程序输出 (stdout)]\n{stdout}\n"
        if ai_fb:
            output += f"\n[沙箱AI初步分析]\n{ai_fb}\n"
        if not stderr and not stdout:
            output += "\n（程序运行完毕，无任何输出）\n"
        return output

    except httpx.ConnectError:
        return "[工具错误] 沙箱服务未启动（连不上 127.0.0.1:8002），请检查 Sandbox Agent 是否运行中。"
    except httpx.HTTPStatusError as e:
        return f"[工具错误] 沙箱返回 HTTP {e.response.status_code}：{e.response.text[:200]}"
    except Exception as e:
        logger.error(f"Sandbox execution failed: {e}")
        return f"[工具错误] 沙箱调用异常：{str(e)}"


# =========================================================
# 工具2: web_search — 搜索 C++ 文档/报错信息
# =========================================================

@tool
async def web_search(query: str) -> str:
    """
    在互联网上搜索 C++ 相关文档、编译器报错含义或标准库用法。

    当遇到以下情况时调用此工具：
    - 用户代码里出现了你不确定的 C++17/20 语言特性
    - 遇到冷门的编译器报错信息（如 "use of deleted function"）
    - 需要验证某个 STL 函数的精确签名或行为

    Args:
        query: 搜索词，例如 "std::vector erase iterator invalidation c++"

    Returns:
        包含相关搜索结果摘要的字符串。
    """
    try:
        from langchain_community.tools import DuckDuckGoSearchResults
        search = DuckDuckGoSearchResults(max_results=3)
        return search.invoke(query)
    except ImportError:
        return "工具错误：langchain_community 或 duckduckgo-search 未安装。"
    except Exception as e:
        return f"搜索失败：{str(e)}"


# =========================================================
# 工具3: analyze_time_complexity — 分析代码的时间/空间复杂度
# =========================================================

@tool
async def analyze_complexity(code: str, problem_description: str = "") -> str:
    """
    分析用户提交的 C++ 代码的时间复杂度和空间复杂度，并指出是否存在性能瓶颈。

    当以下情况时调用此工具：
    - 用户的代码逻辑正确但题目提示"超时（TLE）"
    - 用户的代码使用了嵌套循环或递归，需要判断复杂度是否合理
    - 学生主动询问自己代码的时间/空间效率

    Args:
        code: 要分析的完整 C++ 代码。
        problem_description: 可选，题目描述（帮助判断数据规模约束）。

    Returns:
        时间复杂度和空间复杂度分析报告，以及是否存在性能问题的结论。
    """
    import os
    from openai import AsyncOpenAI

    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    prompt = f"""请分析以下 C++ 代码的时间复杂度和空间复杂度。

题目背景（如有）：
{problem_description if problem_description else '未提供'}

代码：
```cpp
{code}
```

请给出：
1. 时间复杂度（Big-O）
2. 空间复杂度（Big-O）
3. 主要瓶颈在哪里（如嵌套循环、递归深度、额外数组等）
4. 如果题目数据范围是 n<=10^5，这个复杂度是否能通过？

只输出分析结果，不要给出完整修正代码。"""

    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[复杂度分析失败] {str(e)}"


# =========================================================
# 工具4: get_similar_hint — 给出类同类型题目的模式提示（不给答案）
# =========================================================

@tool
async def get_similar_hint(problem_description: str, error_type: str = "") -> str:
    """
    根据题目类型和当前错误，引导学生思考正确的解题方向，但不直接给出答案。

    当以下情况时调用此工具：
    - 学生完全没头绪，不知道该用什么算法
    - 学生卡在某个步骤超过了两轮对话还没有进展
    - 沙箱报告了 Wrong Answer，需要给出算法层面的提示

    Args:
        problem_description: 题目描述内容。
        error_type: 可选，当前的错误类型（如 "Wrong Answer", "TLE", "无从下手"）。

    Returns:
        苏格拉底式的算法方向启发（描述解题模式，不给完整算法）。
    """
    import os
    from openai import AsyncOpenAI

    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    prompt = f"""你是一个苏格拉底式的编程导师。

学生正在解决以下问题：
{problem_description}

当前遇到的困难/错误类型：{error_type if error_type else '没有具体说明'}

请提供：
1. 这道题属于什么类型的算法问题（如：双指针、动态规划、BFS等）？
2. 解这类题时有什么关键的思路模式值得思考？（用问句引导，如"你有没有想过..."）
3. 一个没有答案的提示问题，让学生自己去思考下一步。

规则：不要给出完整代码，不要直接说出答案，只用提问和模式引导。"""

    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[提示生成失败] {str(e)}"


# 暴露给 TutorAgent 的工具列表
tutor_tools = [run_sandbox_code, web_search, analyze_complexity, get_similar_hint]
