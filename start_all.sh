#!/bin/bash

echo "=========================================="
echo "    One-Click AI Service Launcher"
echo "=========================================="

# ─── 工具函数：等待端口释放 ─────────────────────────────
wait_port_free() {
    local port=$1
    local max_wait=10
    local i=0
    while sudo lsof -i :$port -sTCP:LISTEN -t > /dev/null 2>&1; do
        if [ $i -ge $max_wait ]; then
            echo "[ERROR] Port $port still in use after ${max_wait}s. Aborting."
            exit 1
        fi
        echo "  Waiting for port $port to be free... ($i/${max_wait}s)"
        sleep 1
        i=$((i + 1))
    done
}

# ─── 0. 先停掉所有旧服务 ─────────────────────────────────
echo "[0/4] Stopping any running services..."
sudo lsof -ti :8000 | xargs -r sudo kill -9 2>/dev/null
sudo lsof -ti :8001 | xargs -r sudo kill -9 2>/dev/null
sudo lsof -ti :8002 | xargs -r sudo kill -9 2>/dev/null
sleep 2  # 等内核回收端口

# ─── 1. 加载 API Keys ────────────────────────────────────
if [ -f "Agent/.env" ]; then
    echo "[1/4] Loading API keys from Agent/.env into environment..."
    export $(grep -v '^#' Agent/.env | grep -v '^$' | xargs)
    echo "Done. DEFAULT_MODEL=$DEFAULT_MODEL"
else
    echo "[WARNING] Agent/.env not found! Skipping key loading."
fi

# ─── 2. 启动 Tutor Agent (Port 8001) ─────────────────────
echo "[2/4] Starting Tutor Agent on Port 8001..."
wait_port_free 8001
cd Agent/TurorAgent
nohup uvicorn main:app --host 0.0.0.0 --port 8001 > tutor.log 2>&1 &
TUTOR_PID=$!
echo "Tutor Agent PID: $TUTOR_PID"
cd ../..

# ─── 3. 启动 Sandbox Agent (Port 8002) ───────────────────
echo "[3/4] Starting Sandbox Agent on Port 8002..."
wait_port_free 8002
cd Agent/SandBoxAgent
nohup python3 sandbox_api.py > sandbox.log 2>&1 &
SANDBOX_PID=$!
echo "Sandbox Agent PID: $SANDBOX_PID"
cd ../..

# ─── 4. 启动 C++ HttpServer (Port 8000) ──────────────────
echo "[4/4] Starting C++ HttpServer on Port 8000..."
wait_port_free 8000
cd build
nohup ./http_server -p 8000 > httpserver.log 2>&1 &
HTTP_PID=$!
echo "HttpServer PID: $HTTP_PID"
cd ..

echo "=========================================="
echo "All services started!"
echo ""
echo "📄 实时日志:"
echo "  tail -f build/httpserver.log"
echo "  tail -f Agent/TurorAgent/tutor.log"
echo "  tail -f Agent/SandBoxAgent/sandbox.log"
echo ""
echo "🔴 停止所有服务:"
echo "  sudo lsof -ti :8000,:8001,:8002 | xargs -r sudo kill -9"
echo "=========================================="
