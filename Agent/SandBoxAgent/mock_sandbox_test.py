import asyncio
from executor import execute_code_sandboxed

async def test_security_scenarios():
    print("🚀 开始沙箱安全能力测试...\n")

    # 1. 测试网络隔离 (应该报错)
    print("测试 1: 网络隔离测试 (尝试访问百度)...")
    net_code = "import urllib.request\ntry:\n    urllib.request.urlopen('http://www.baidu.com', timeout=2)\n    print('FAIL: Network is accessible')\nexcept:\n    print('SUCCESS: Network is blocked')"
    res = await execute_code_sandboxed("python", net_code, "")
    print(f"结果: {res['stdout'].strip() or res['stderr'].strip()}\n")

    # 2. 测试内存限制 (应该触发 TLE 或被 Kill)
    print("测试 2: 内存限制测试 (尝试分配 1GB 内存)...")
    mem_code = "print('Allocating...'); a = [1] * (1024 * 1024 * 200); print('Done')"
    res = await execute_code_sandboxed("python", mem_code, "")
    print(f"状态: {res['status']}, 错误信息: {res['stderr'].strip()}\n")

    # 3. 测试文件系统隔离 (查看根目录)
    print("测试 3: 文件系统隔离 (查看根目录内容)...")
    fs_code = "import os; print(os.listdir('/'))"
    res = await execute_code_sandboxed("python", fs_code, "")
    print(f"结果 (容器内目录): {res['stdout'].strip()}\n")

    # 4. 测试 C++ 死循环 (应该返回 Time Limit Exceeded)
    print("测试 4: C++ 超时测试 (死循环)...")
    cpp_code = "#include <iostream>\nint main() { while(true); return 0; }"
    res = await execute_code_sandboxed("cpp", cpp_code, "")
    print(f"状态: {res['status']}\n")

if __name__ == "__main__":
    asyncio.run(test_security_scenarios())
