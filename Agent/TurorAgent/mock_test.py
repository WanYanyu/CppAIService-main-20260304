import asyncio
import json
from models import TutorChatRequest, ChatMessage
from tutor_agent import process_tutor_request
import os

# 确保在运行前你的 .env 文件里配置了 DEEPSEEK_API_KEY
from dotenv import load_dotenv
load_dotenv()

async def run_mock_test():
    print("=== 正在测试 Socratic Tutor Agent (DeepSeek) ===\n")
    if not os.getenv("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY") == "your_api_key_here":
        print("敬告：请先在 .env 文件中填入真正的 DEEPSEEK_API_KEY 才能运行测试。")
        return

    # 模拟前端发来的请求结构
    mock_request = TutorChatRequest(
        problem_id="1",
        problem_description="给定一个非空整数数组，除了某个元素只出现一次以外，其余每个元素均出现两次。找出那个只出现了一次的元素。请实现线性时间复杂度的算法且不使用额外空间。",
        current_code='''def singleNumber(nums):
    res = []
    for n in nums:
        if n in res:
            res.remove(n)
        else:
            res.append(n)
    return res[0]
''',
        test_case_results="Wrong Answer: Time Limit Exceeded 或者由于使用了额外空间(res 数组)不符合题目 O(1) 空间复杂度的要求。",
        chat_history=[
            ChatMessage(role="user", content="我的代码哪里有问题？能不能直接把正确的代码写出来给我看看？")
        ],
        user_message="我就想要正确答案，求求你了告诉我吧。"
    )

    print("【前端发送的数据载荷】:")
    print(mock_request.model_dump_json(indent=2))
    print("-" * 50)
    print("Agent 处理中，请稍候...\n")

    response = await process_tutor_request(mock_request)

    print("【节点1：后台专家隐式分析结果】 (不展示给用户)")
    print(response.error_analysis)
    print("-" * 50)
    print("【节点2：导师启发式回复】 (展示给用户)")
    print(response.reply)
    print("===================================================\n")

if __name__ == "__main__":
    asyncio.run(run_mock_test())
