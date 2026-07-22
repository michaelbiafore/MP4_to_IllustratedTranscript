Here's the complete proxy rotation system — 6 source files, ~900 lines total.

Files
File	Responsibility
src/proxy-pool.js	IP pool with per-proxy sliding-window quota, error tracking, and banning
src/user-agents.js	Weighted UA bank (Chrome/Firefox/Safari/Edge) + full buildHeaders() with Sec-CH-UA, Sec-Fetch-, DNT
src/request-queue.js	Priority queue with Gaussian delay (Box-Muller) + random reading pauses
src/proxy-client.js	Orchestrator — ties pool + queue + backoff together; exposes get(), post(), fetchYouTubePage(), fetchTranscript()
src/transport.js	Clean CONNECT-tunnel transport via http-proxy-agent / https-proxy-agent
src/example.js	Batch transcript fetching, video page retrieval, pool stats
Key behaviors
Per-IP quota: Each proxy tracks a sliding 60-second window. acquire() returns the least-used proxy that hasn't hit 10 req/min. When all are at quota, msUntilAvailable() calculates exactly how long to sleep until the earliest slot opens.

Exponential backoff (full-jitter): On a 429, the proxy is immediately banned for 5 min. The retry waits random(0, min(60s, 1s × 2^attempt)). Retry-After headers (both seconds and HTTP-date format) are parsed and respected.

UA rotation: Weighted sampling — Chrome on Windows has 20× the weight of Firefox on Linux, mirroring real traffic. Each request gets a full header set including matching Sec-CH-UA, Sec-CH-UA-Platform, Sec-Fetch-*, and ~30% DNT variation.

Human queue: Three priority lanes (high/normal/low). Each worker waits a Gaussian-distributed delay after completing (μ=2500ms, σ=900ms, clamped to 500–8000ms), plus a 12% chance of a 5–20s "reading pause" before the next pickup.

Setup
bash
unzip proxy-rotator.zip && cd proxy-rotator
npm install
PROXY_LIST_PATH=./proxies.json node src/example.js
Your proxies.json should be an array of { host, port, username, password } objects. Bright Data, Oxylabs, Smartproxy, and Webshare all work with the format shown in the README. For per-port sticky sessions (most common residential format), use the 10001 + i port offset pattern shown in example.js.