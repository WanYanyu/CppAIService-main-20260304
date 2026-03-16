import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
    vus: 10,
    duration: '30s',
};

export default function () {
    const res = http.get('http://106.53.19.125:8000/');
    check(res, {
        'status is 200': (r) => r.status === 200,
    });
    sleep(1);
}

export function handleSummary(data) {
    const text = `
k6 test summary
================
http_req_failed: ${data.metrics.http_req_failed?.values?.rate ?? 'N/A'}
http_reqs: ${data.metrics.http_reqs?.values?.count ?? 'N/A'}
avg_duration: ${data.metrics.http_req_duration?.values?.avg ?? 'N/A'} ms
min_duration: ${data.metrics.http_req_duration?.values?.min ?? 'N/A'} ms
med_duration: ${data.metrics.http_req_duration?.values?.med ?? 'N/A'} ms
max_duration: ${data.metrics.http_req_duration?.values?.max ?? 'N/A'} ms
p90_duration: ${data.metrics.http_req_duration?.values['p(90)'] ?? 'N/A'} ms
p95_duration: ${data.metrics.http_req_duration?.values['p(95)'] ?? 'N/A'} ms
iterations: ${data.metrics.iterations?.values?.count ?? 'N/A'}
vus_max: ${data.metrics.vus_max?.values?.max ?? 'N/A'}
checks_passed: ${data.metrics.checks?.values?.passes ?? 'N/A'}
checks_failed: ${data.metrics.checks?.values?.fails ?? 'N/A'}
`;

    const now = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `result_${now}.txt`;

    return {
        stdout: text,
        [filename]: text,
    };
}
