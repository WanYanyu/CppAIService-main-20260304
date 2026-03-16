from pydantic import BaseModel, Field
from typing import List, Optional

class TestCase(BaseModel):
    input: str = Field(..., description="标准输入字符串", example="2\n[2,7,11,15]\n9")
    expected_output: str = Field(..., description="预期标准输出字符串", example="[0,1]")

class EvaluationRequest(BaseModel):
    language: str = Field(..., description="编程语言，如 'python', 未来支持 'cpp'", example="python")
    code: str = Field(..., description="用户提交的代码文本")
    test_cases: List[TestCase] = Field(..., description="要运行的测试样例数组")

class EvaluationResult(BaseModel):
    status: str = Field(..., description="执行状态: 'Passed', 'Wrong Answer', 'Time Limit Exceeded', 'Runtime Error', 'Compilation Error'")
    stdout_log: Optional[str] = Field(None, description="标准输出全量日志")
    stderr_log: Optional[str] = Field(None, description="标准错误/报错回溯(Traceback)")
    ai_feedback: Optional[str] = Field(None, description="AI 基于真实报错生成的自然语言评测报告")
