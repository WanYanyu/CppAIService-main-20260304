import asyncio
import os
import subprocess
import tempfile
from typing import Tuple, Dict, Any

# ==========================================
# 沙盒物理执行核心逻辑: Tool Calling
# ==========================================

async def run_python_code(code: str, test_input: str, timeout_seconds: int = 3) -> Dict[str, Any]:
    """
    接收 Python 代码和单条测试输入，安全地在子进程里执行。
    返回带状态、stdout 和 stderr 的字典。
    """
    # 建立一个临时文件存放用户的代码
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as temp_py_file:
        temp_py_file.write(code)
        temp_file_path = temp_py_file.name

    try:
        # 使用 asyncio.create_subprocess_exec 防止阻塞 FastAPI 的总线程
        process = await asyncio.create_subprocess_exec(
            "python3", temp_file_path,  # ✅ FIXED: 服务器上用 python3，不是 python
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            # 灌入测试输入，等待并设置超时
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=test_input.encode('utf-8')),
                timeout=timeout_seconds
            )

            return {
                "status": "Finished",
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "return_code": process.returncode
            }

        except asyncio.TimeoutError:
            # 执行超时：物理强杀进程组，防止死循环
            try:
                process.kill()
            except Exception:
                pass
            return {
                "status": "Time Limit Exceeded",
                "stdout": "",
                "stderr": f"Code execution timed out after {timeout_seconds} seconds.",
                "return_code": -1
            }
    finally:
        # 无论成功失败，都要清理掉宿主机上的临时 Python 脚本
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

async def run_cpp_code(code: str, test_input: str, timeout_seconds: int = 3) -> Dict[str, Any]:
    """为 C++ 源码执行 编译 -> 运行 流程"""
    # 建立一个临时文件存放用户的代码
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False, encoding='utf-8') as temp_cpp_file:
        temp_cpp_file.write(code)
        temp_cpp_path = temp_cpp_file.name

    # 对应编译出的二进制文件路径 (Windows 环境为 .exe)
    if os.name == 'nt':
        exe_path = temp_cpp_path.replace('.cpp', '.exe')
    else:
        exe_path = temp_cpp_path.replace('.cpp', '.out')

    try:
        # 阶段 1: 编译 (Compile)
        compile_process = await asyncio.create_subprocess_exec(
            "g++", temp_cpp_path, "-o", exe_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        cmp_stdout, cmp_stderr = await compile_process.communicate()

        if compile_process.returncode != 0:
            # 编译失败直接返回
            return {
                "status": "Compilation Error",
                "stdout": "",
                "stderr": cmp_stderr.decode('utf-8', errors='replace'),
                "return_code": compile_process.returncode
            }

        # 阶段 2: 运行预编译的二进制可执行文件 (Execute)
        run_process = await asyncio.create_subprocess_exec(
            exe_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            # 灌入测试输入，等待超时控制
            r_stdout, r_stderr = await asyncio.wait_for(
                run_process.communicate(input=test_input.encode('utf-8')),
                timeout=timeout_seconds
            )

            return {
                "status": "Finished",
                "stdout": r_stdout.decode('utf-8', errors='replace'),
                "stderr": r_stderr.decode('utf-8', errors='replace'),
                "return_code": run_process.returncode
            }

        except asyncio.TimeoutError:
            try:
                run_process.kill()
            except Exception:
                pass
            return {
                "status": "Time Limit Exceeded",
                "stdout": "",
                "stderr": f"Code execution timed out after {timeout_seconds} seconds.",
                "return_code": -1
            }

    finally:
        # 无论成功失败，都要清理掉宿主机上的临时文件 (.cpp 和 .exe)
        if os.path.exists(temp_cpp_path):
            try:
                os.remove(temp_cpp_path)
            except Exception: pass
        if os.path.exists(exe_path):
            try:
                os.remove(exe_path)
            except Exception: pass

async def execute_code_sandboxed(language: str, code: str, test_input: str, timeout: int = 3) -> Dict[str, Any]:
    """路由层：根据语言派发物理工具"""
    if language.lower() == 'python':
        return await run_python_code(code, test_input, timeout)
    elif language.lower() in ('cpp', 'c++'):
        return await run_cpp_code(code, test_input, timeout)
    else:
        return {
            "status": "Error",
            "stdout": "",
            "stderr": f"Unsupported language: {language}\nCurrently only Python and C++ are supported.",
            "return_code": -1
        }
