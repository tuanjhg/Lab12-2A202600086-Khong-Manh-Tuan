# Deployment Information

## Public URL
https://day12-production-960d.up.railway.app

https://focused-learning-production-ff4b.up.railway.app

## Platform
Railway

## Test Commands

### 1. Health Check
```bash
curl https://day12-production-960d.up.railway.app/health
# Expected: {"status": "ok", "redis_connection": "connected", ...}
```

### 2. Ready Check
```bash
curl https://day12-production-960d.up.railway.app/ready
# Expected: {"ready": true}
```

### 3. API Test (Requires Authentication)
```bash
# Thay <YOUR_AGENT_API_KEY> bằng API Key bạn đã set trong environment variables
curl -X POST https://day12-production-960d.up.railway.app/ask \
  -H "X-API-Key: <YOUR_AGENT_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Docker multi-stage build?"}'
```

## Environment Variables Set
| Key | Description | Example Value |
|-----|-------------|---------------|
| `PORT` | Cổng ứng dụng chạy (Railway tự cấp) | `8000` |
| `ENVIRONMENT` | Môi trường chạy | `production` |
| `REDIS_URL` | Đường dẫn kết nối Redis | `redis://...` |
| `AGENT_API_KEY` | Key bảo mật cho API | `********` |
| `RATE_LIMIT_PER_MINUTE` | Giới hạn request mỗi phút | `20` |
| `DAILY_BUDGET_USD` | Ngân sách token mỗi ngày | `10.0` |
