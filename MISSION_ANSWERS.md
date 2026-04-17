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




