import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from models import EvaluationRequest, EvaluationResult, TestCase
from executor import execute_code_sandboxed
from prompts import SANDBOX_DIAGNOSIS_PROMPT

load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY", "")
base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

client = AsyncOpenAI(api_key=api_key, base_url=base_url)
MODEL_NAME = "deepseek-chat" # "deepseek-coder" is also acceptable

async def evaluate_code(request: EvaluationRequest) -> EvaluationResult:
    """The main orchestration function for Sandbox Evaluation"""
    total_stdout = ""
    total_stderr = ""
    run_status = "Passed" # Default assumes it passes everything
    failed_execution_status = ""

    # 1. Physical Execution Phase
    if not request.test_cases:
        request.test_cases = [TestCase(input="", expected_output="")]

    for idx, tc in enumerate(request.test_cases):
        # Tools: run the code in an isolated subprocess
        exec_result = await execute_code_sandboxed(
            language=request.language,
            code=request.code,
            test_input=tc.input,
            timeout=3
        )

        # Collect logs
        total_stdout += f"--- Test Case {idx + 1} ---\n{exec_result['stdout']}\n"

        if exec_result['stderr']:
            total_stderr += f"--- Test Case {idx + 1} Error ---\n{exec_result['stderr']}\n"

        # Check standard errors, timeouts, or output mismatches
        if exec_result["return_code"] != 0 or exec_result['status'] in ("Time Limit Exceeded", "Compilation Error"):
            # Preserve Compilation Error and Time Limit Exceeded, otherwise it's a Runtime Error
            if exec_result['status'] in ("Compilation Error", "Time Limit Exceeded"):
                run_status = exec_result['status']
            else:
                run_status = "Runtime Error"

            failed_execution_status = f"Test Case {idx + 1}: Process exited with status {exec_result['status']} (code {exec_result['return_code']})."
            break # 只要错了一个就短路拦截

        # If expected_output is completely empty, it means the user hasn't configured test cases for this problem.
        # We shouldn't automatically pass it if it ran without errors, but we can't do a string match either.
        # For now, let's treat it as Passed (since it didn't crash), but note it later if needed.
        elif tc.expected_output and exec_result['stdout'].strip() != tc.expected_output.strip():
            run_status = "Wrong Answer"
            failed_execution_status = f"Test Case {idx + 1}: Output mismatch.\nExpected: {tc.expected_output}\nGot: {exec_result['stdout']}"
            break # 答案错也直接拦截


    # 2. AI Diagnosis Phase
    ai_feedback = None
    # We trigger AI diagnosis if there's a definite failure, OR if we "passed" but no expected output was provided
    # (so we don't actually know if it's correct without AI judging the raw output).
    needs_ai_judgment = False
    if run_status != "Passed":
        needs_ai_judgment = True
    elif all(not tc.expected_output for tc in request.test_cases):
        # All test cases had empty expected outputs, so the "Passed" status from execution is fake.
        # We must ask the AI to evaluate the code and stdout.
        needs_ai_judgment = True
        run_status = "Unverified" # Change status so frontend doesn't show a bold green "Passed"
        failed_execution_status = (
            "【极端重要说明】代码成功编译并且完美执行结束，没有发生任何崩溃！仅仅是因为用户没有设置预期输出答案，所以系统标记为待验证。\n"
            "你的任务是：如果代码逻辑大体正确，请**极其强烈地表扬**用户，直接告诉用户代码非常好，完全没问题！\n"
            "**绝对禁止**去鸡蛋里挑骨头，**绝对禁止**去捏造不存在的语法错误或逻辑漏洞（比如认为 `a ? b : c` 和 `if else` 其中之一是错的）。"
        )

    if needs_ai_judgment:
        diagnosis_prompt = SANDBOX_DIAGNOSIS_PROMPT.format(
            user_code=request.code,
            execution_status=failed_execution_status,
            stdout=total_stdout,
            stderr=total_stderr
        )

        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": diagnosis_prompt}],
            temperature=0.3, # 稍微带点温度以生成人类友好的话术
        )
        ai_feedback = response.choices[0].message.content

        # If the AI explicitly says it's correct in its own way, we could theoretically parse it,
        # but for now we'll just return the feedback under the "Unverified" or "Wrong Answer" status.
    else:
        ai_feedback = "恭喜你！代码成功通过了所有的沙盒测试用例，逻辑非常完美！"

    return EvaluationResult(
        status=run_status,
        stdout_log=total_stdout,
        stderr_log=total_stderr,
        ai_feedback=ai_feedback
    )
