import os
import asyncio
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
    has_expected_output = any((tc.expected_output or "").strip() for tc in request.test_cases)

    # 没有任何 expected_output 时，不得输出“代码正确”的结论
    if run_status == "Passed" and not has_expected_output:
        run_status = "Unverified"
        ai_feedback = (
            "当前没有可用于判题的 expected_output，系统只能确认“可编译且可运行”，"
            "不能确认“题目答案正确”。请先补充有效测试样例后再判断是否通过。"
        )

    # We trigger AI diagnosis if there's a definite failure, OR if we "passed" but no expected output was provided
    # (so we don't actually know if it's correct without AI judging the raw output).
    needs_ai_judgment = False
    if run_status != "Passed" and run_status != "Unverified":
        needs_ai_judgment = True

    if needs_ai_judgment:
        diagnosis_prompt = SANDBOX_DIAGNOSIS_PROMPT.format(
            user_code=request.code,
            execution_status=failed_execution_status,
            stdout=total_stdout,
            stderr=total_stderr
        )

        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": diagnosis_prompt}],
                    temperature=0.3, # 稍微带点温度以生成人类友好的话术
                ),
                timeout=10,
            )
            ai_feedback = response.choices[0].message.content
        except Exception as e:
            ai_feedback = (
                "AI 诊断暂时不可用（已超时或调用失败），但沙盒执行结果已返回。"
                f" 失败原因: {str(e)}"
            )

        # If the AI explicitly says it's correct in its own way, we could theoretically parse it,
        # but for now we'll just return the feedback under the "Unverified" or "Wrong Answer" status.
    elif ai_feedback is None:
        ai_feedback = "恭喜你！代码成功通过了所有的沙盒测试用例，逻辑非常完美！"

    return EvaluationResult(
        status=run_status,
        stdout_log=total_stdout,
        stderr_log=total_stderr,
        ai_feedback=ai_feedback
    )
