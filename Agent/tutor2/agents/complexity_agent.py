import asyncio
from openai import AsyncOpenAI
from ..config import settings


async def run_complexity_agent(code: str, problem_description: str) -> dict:
    if not settings.llm_api_key:
        return {
            "text": "未配置 LLM API Key，无法分析复杂度。",
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }

    client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
    prompt = f"""请分析下面 C++ 代码复杂度，输出：\n1) 时间复杂度\n2) 空间复杂度\n3) 是否可能超时\n4) 一条优化建议（不要给完整代码）\n\n题目描述：\n{problem_description}\n\n代码：\n```cpp\n{code}\n```"""

    try:
        resp = await asyncio.wait_for(
            client.chat.completions.create(
                model=settings.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            ),
            timeout=12,
        )
        usage = getattr(resp, "usage", None)
        return {
            "text": resp.choices[0].message.content or "复杂度分析为空。",
            "token_usage": {
                "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
                "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
                "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
            },
        }
    except Exception as e:
        return {
            "text": f"复杂度分析失败: {e}",
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
