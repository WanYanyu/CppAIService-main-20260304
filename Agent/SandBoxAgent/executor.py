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
    接收 Python 代码和单条测试输入，安全地在 Docker 沙盒中执行。
    返回带状态、stdout 和 stderr 的字典。
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_py_path = os.path.join(temp_dir, 'solution.py')
        with open(temp_py_path, 'w', encoding='utf-8') as f:
            f.write(code)

        try:
            # 使用 Docker 拉起隔离的 Python 容器
            process = await asyncio.create_subprocess_exec(
                "docker", "run", "--rm", "-i",
                "--net", "none",             # 断开网络
                "--memory", "256m",          # 限制内存
                "--cpus", "1.0",             # 限制 CPU 使用
                "-v", f"{temp_dir}:/sandbox",
                "-w", "/sandbox",
                "python:3.9-slim",
                "python3", "solution.py",
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
                    "status": "Finished" if process.returncode == 0 else "Runtime Error",
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
        except Exception as e:
            return {
                "status": "System Error",
                "stdout": "",
                "stderr": f"Docker container error: {str(e)}",
                "return_code": -1
            }

async def run_cpp_code(code: str, test_input: str, timeout_seconds: int = 3) -> Dict[str, Any]:
    """为 C++ 源码执行 编译 -> 运行 流程 (基于 Docker 沙盒)"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_cpp_path = os.path.join(temp_dir, 'solution.cpp')
        with open(temp_cpp_path, 'w', encoding='utf-8') as f:
            f.write(code)

        try:
            # 阶段 1: 容器内编译 (Compile)
            compile_process = await asyncio.create_subprocess_exec(
                "docker", "run", "--rm",
                "--net", "none",
                "-v", f"{temp_dir}:/sandbox",
                "-w", "/sandbox",
                "gcc:latest",
                "g++", "solution.cpp", "-o", "a.out",
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

            # 阶段 2: 容器内运行 (Execute) 带有严格的资源限制
            run_process = await asyncio.create_subprocess_exec(
                "docker", "run", "--rm", "-i",
                "--net", "none",            # 禁用网络
                "--memory", "256m",         # 限制内存读写 256MB
                "--cpus", "1.0",            # 限制单核性能
                "-v", f"{temp_dir}:/sandbox",
                "-w", "/sandbox",
                "gcc:latest",
                "./a.out",
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
                    "status": "Finished" if run_process.returncode == 0 else "Runtime Error",
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
        except Exception as e:
            return {
                "status": "System Error",
                "stdout": "",
                "stderr": f"Docker container error: {str(e)}",
                "return_code": -1
            }

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
