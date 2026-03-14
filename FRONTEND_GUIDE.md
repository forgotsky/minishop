# Frontend Guide (Simple)

This branch ships only the H5 build of uni-app for a minimal Docker deployment.

## Code location
- uni-app app: `uni-app/`
- Main pages: `uni-app/pages/*`
- API config: `uni-app/utils/api.js`

## Configure API URL
Edit `uni-app/utils/api.js` before building:

```js
const DEFAULT_BASE_URL = "http://<SERVER_IP>:8000";
```

## Build & run (Docker)
```bash
cd /root/codex/uni-app
docker build -t skill-frontend:latest .

docker run -d --name skill-frontend -p 5174:80 skill-frontend:latest
```

Open:
- `http://<SERVER_IP>:5174`
