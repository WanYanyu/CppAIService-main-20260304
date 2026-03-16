import asyncio
import os
import json
from dotenv import load_dotenv

load_dotenv()

from models import EvaluationRequest, TestCase
from sandbox_agent import evaluate_code

async def run_cpp_sandbox_tests():
    print("=== 正在运行沙盒评测 Agent (SandBoxAgent) C++ 环境验证测试 ===\n")
    
    # 测试场景 1: C++ 编译报错 (Compilation Error)
    print("▶ 测试场景 1: 真实执行发生 C++ 编译报错 (漏了分号)")
    req_compile_error = EvaluationRequest(
        language="cpp",
        code="""
#include <iostream>
using namespace std;

int main() {
    int a, b;
    cin >> a >> b;
    // 故意漏掉分号导致编译不通过
    cout << a + b
    return 0;
}
""",
        test_cases=[
            TestCase(input="3 5", expected_output="8")
        ]
    )
    
    res1 = await evaluate_code(req_compile_error)
    print(f"【执行状态】: {res1.status}")
    print(f"【AI诊断报告】:\n{res1.ai_feedback}")
    print("-" * 60)

    # 测试场景 2: C++ 逻辑错误或 Runtime Error 测试
    print("▶ 测试场景 2: C++ 逻辑错误 (Wrong Answer 因变量未初始化)")
    req_wrong_answer = EvaluationRequest(
        language="cpp",
        code="""
#include <iostream>
using namespace std;

int main() {
    int a, b;
    int sum;
    cin >> a >> b;
    // 故意没有赋值直接累加，这在 C++ 会产生内存垃圾值导致 WA
    sum += a + b;
    cout << sum << endl;
    return 0;
}
""",
        test_cases=[
            TestCase(input="10 20", expected_output="30\n")
        ]
    )
    
    res2 = await evaluate_code(req_wrong_answer)
    print(f"【执行状态】: {res2.status}")
    print(f"【AI诊断报告】:\n{res2.ai_feedback}")
    print("========================================================\n")

if __name__ == "__main__":
    asyncio.run(run_cpp_sandbox_tests())
