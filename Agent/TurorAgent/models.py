from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ChatMessage(BaseModel):
    role: str # "user", "assistant", "system"
    content: str
    
class TutorChatRequest(BaseModel):
    problem_id: str = Field(..., description="题号", example="1")
    problem_description: str = Field(..., description="题目描述", example="实现两数之和。给定一个整数数组 nums 和一个整数目标值 target，请你在该数组中找出和为目标值的那两个整数，并返回它们的数组下标。")
    current_code: str = Field(..., description="当前编辑器里的全部代码", example="def twoSum(nums, target):\n    return []")
    test_case_results: Optional[str] = Field(None, description="评测机返回的错误信息或跑失败的测例", example="Wrong Answer: Output: [], Expected: [0, 1]")
    chat_history: List[ChatMessage] = Field(default_factory=list, description="历史交互记录")
    user_message: str = Field("", description="本次用户在聊天框输入的问题", example="我的代码哪里错了？")

class TutorChatResponse(BaseModel):
    reply: str = Field(..., description="Agent的苏格拉底式启发问题或小提示")
    error_analysis: Optional[str] = Field(None, description="后台专家隐式错误分析(仅供测试用,前端可选是否展示)")
