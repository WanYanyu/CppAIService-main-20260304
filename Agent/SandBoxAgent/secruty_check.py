import asyncio
from executor import execute_code_sandboxed

async def main():
    print("🛡️  正在启动沙箱安全防御测试...\n")

    # 测试 1: 尝试访问外部网络
    print("【测试 1: 网络隔离】 尝试爬取网页...")
    net_code = "import urllib.request\ntry:\n    urllib.request.urlopen('http://www.google.com', timeout=2)\n    print('FAIL: 居然能上网！')\nexcept:\n    print('SUCCESS: 网络已封死。')"
    res = await execute_code_sandboxed("python", net_code, "")
    print(f"结果: {res['stdout'].strip()}\n")

    # 测试 2: 尝试读取宿主机根目录
    print("【测试 2: 文件隔离】 尝试窥探宿主机根目录...")
    fs_code = "import os\nprint('容器内根目录内容:', os.listdir('/'))"
    res = await execute_code_sandboxed("python", fs_code, "")
    print(f"结果: {res['stdout'].strip()}\n")

    # 测试 3: 尝试耗尽内存 (256MB 限制)
    print("【测试 3: 资源限制】 尝试申请超大内存...")
    mem_code = "print('申请内存中...'); a = [1] * (1024 * 1024 * 100); print('申请成功')"
    res = await execute_code_sandboxed("python", mem_code, "")
    print(f"执行状态: {res['status']} (非 Finished 说明被 Docker 强杀了)\n")

    # 测试 4: C++ 编译与运行测试
    print("【测试 4: C++ 链路】 验证 C++ 容器化编译运行...")
    cpp_code = "#include <iostream>\nint main() { std::cout << \"Hello from C++ Sandbox!\"; return 0; }"
    res = await execute_code_sandboxed("cpp", cpp_code, "")
    print(f"结果: {res['stdout'].strip()}\n")

if __name__ == "__main__":
    asyncio.run(main())
