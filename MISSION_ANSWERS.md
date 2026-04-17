ID : 2A202600086
Name : KHỔNG MẠNH TUẤN 

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found
1. API keys hardcoded in source code
2. no config management (e.g. .env files)
3. print statements for debugging instead of proper logging
4. no health checks or monitoring
5. stateful design (e.g. in-memory data)
6. port binding to localhost only
### Exercise 1.3: Comparison table

| Feature | Basic | Advanced | Tại sao quan trọng? |
|---------|-------|----------|---------------------|
| Config | Hardcode | Env vars | lộ API keys |
| Health check |  |  | Cho phép giám sát và tự động khởi động lại |
| Logging | print() | JSON | Cung cấp thông tin chi tiết hơn cho việc gỡ lỗi và giám sát |
| Shutdown | Đột ngột | Graceful | ngăn chặn mất dữ liệu và cho phép dọn dẹp khi tắt máy |


## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. Base image: các image sẵn đã được cài không cần build lại (python:3.11)
2. Working directory: /app
3. Sử dụng multi-stage build để giảm kích thước image bằng cách chỉ copy file cần thiết vào final image
4. CMD cung cấp lệnh mặc định có thể bị ghi đè khi chạy container, trong khi ENTRYPOINT xác định lệnh không thể bị ghi đè và luôn được thực thi.

image size : 1.66GB
### Exercise 2.3: Image size comparison

image size : 
- Develop: 1.66 GB
- Production: 236 MB

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment
- URL: https://day12-production-960d.up.railway.app
- Screenshot: ../03-cloud-deployment/railway/evidence.png 

## Part 4: API Security

### Exercise 4.1-4.3: Test results
4.1: missing api key , bad hostname 
4.2: valid api key, valid hostname
4.3: valid api key, valid hostname, rate limit exceeded

### Exercise 4.4: Cost guard
- Quản lý chi phí bằng Redis thay vì RAM (in-memory).
- Gọi `redis.pipeline()` để tăng (incr) token usage và thiết lập thời hạn lưu trữ (TTL) nhằm giới hạn request (dùng HTTPException 402 nếu vượt `DAILY_BUDGET_USD`).

## Part 5: Scaling & Reliability

### Exercise 5.1: Health checks
- `/health`: Liveness probe (kiểm tra `redis.ping()` và tình trạng RAM/CPU) để Cloud platform xem máy chủ còn sống không.
- `/ready`: Readiness probe, phản hồi cho Load Balancer biết instance này đã load xong model và sẵn sàng nhận traffic.

### Exercise 5.2: Graceful shutdown
- Bắt signal `SIGTERM` bằng thư viện signal để chặn request mới.
- Chờ các requests đang handle (in-flight) hoàn thiện trước khi đóng gắt kết nối.

### Exercise 5.3: Stateless design
- Mọi dữ liệu phiên (session), rate limit, cost tracking đều được lưu về backend tập trung là Redis. Bất kỳ node Agent nào cũng có thể xử lý tiếp mà không sợ mất state cục bộ.

### Exercise 5.4: Load balancing
- Sử dụng `Nginx` đóng vai trò upstream, phân tán HTTP request đồng đều tới nhiều instance (ví dụ `replicas: 3`) đã lưu trong `docker-compose.yml`.

## Part 6: Final Project
- Hoàn thiện `my-production-agent`:
  - Image sử dụng Multi-stage builds, non-root user và tự động Healthcheck.
  - Setup `.env.example`, `.dockerignore`, file CI/CD `render.yaml`.
