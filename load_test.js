import http from 'k6/http';
import { check, sleep } from 'k6';

// 1. 配置测试选项，定义压力阶段
export const options = {
    stages: [
        { duration: '30s', target: 50 },  // 爬坡阶段：在 30 秒内并发逐渐增加到 50 个虚拟用户 (VUs)
        { duration: '1m', target: 50 },   // 稳定阶段：保持 50 个并发持续 1 分钟
        { duration: '20s', target: 0 },   // 冷却阶段：在 20 秒内并发降至 0
    ],
    thresholds: {
        // 配置判断阈值，95% 的请求响应时间应当低于 3000ms
        http_req_duration: ['p(95)<3000'],
        // 错误率应低于 1%
        http_req_failed: ['rate<0.01'],
    },
};

// 2. 核心执行逻辑：每个并发用户不断重复执行的动作
export default function () {
    const url = 'http://127.0.0.1:9000/leetcode/fetch';

    // 构造请求体
    const payload = JSON.stringify({
        problemId: 1,
        model: ""
    });

    const params = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    // 发起 POST 请求
    const res = http.post(url, payload, params);

    // 各种断言检查
    check(res, {
        'status is 200': (r) => r.status === 200,
        // 这里还可以对返回的 json 内容进行检查
        // 'has data': (r) => JSON.parse(r.body).data !== undefined,
    });

    // 思考时间 (Think Time) - 防止过度发起死循环请求导致客户端被冲垮
    sleep(1);
}
