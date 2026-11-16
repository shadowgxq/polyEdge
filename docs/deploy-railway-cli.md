# Railway CLI 部署与快速更新

> 本文档针对**用 Railway CLI 直推本地代码**部署到 `vibe-game-solo` 项目的方式（`railway up`），
> 与 [deploy-railway.md](deploy-railway.md)（GitHub 仓库直连、push 自动部署）是两条不同路径，按需选用。
> 适用被部署代码：`vibe_gaming_solo` 仓库下的 `gxq/polyEdge/`（本仓 polyEdge 的副本）。

## 现状速览

| 项 | 值 |
|----|----|
| Railway 项目 | `vibe-game-solo`（Project ID `185f2839-ebec-4085-acab-beec770151f1`） |
| 环境 | `production` |
| Service | `backend`、`frontend`、`Postgres`、`Redis` |
| 部署方式 | Railway CLI `railway up`（直推本地代码，非 GitHub 自动部署） |
| 代码目录（本机） | `~/WorkSpace/vibe_gaming_solo/gxq/polyEdge` |
| 前端地址 | https://frontend-production-2fdf6.up.railway.app |
| 后端地址 | https://backend-production-c92fb.up.railway.app |

## 快速更新部署（日常最常用）

改完代码后，进到对应 service 目录重新 `up` 即可——**变量、域名、link 都已配好，无需重设**。

```bash
# 更新后端（会自动跑 alembic upgrade head 再启动）
cd ~/WorkSpace/vibe_gaming_solo/gxq/polyEdge/backend
railway up -s backend

# 更新前端
cd ~/WorkSpace/vibe_gaming_solo/gxq/polyEdge/frontend
railway up -s frontend
```

- 想立即返回、不盯构建日志：加 `--detach`（`railway up -s backend --detach`）。
- 只改了环境变量、没改代码：直接 `railway variables ... --set 'K=V'`（不加 `--skip-deploys` 会自动触发重部署）。

### 更新后怎么确认成功

```bash
# 后端健康检查 + 真实数据
curl -s https://backend-production-c92fb.up.railway.app/health
curl -s "https://backend-production-c92fb.up.railway.app/api/v1/events?category=hot&page=1" | head -c 200

# 前端页面 + 同源代理到后端
curl -s -o /dev/null -w '%{http_code}\n' https://frontend-production-2fdf6.up.railway.app/
curl -s -o /dev/null -w '%{http_code}\n' "https://frontend-production-2fdf6.up.railway.app/api/v1/events?category=hot&page=1"
```

四条都应是 `200` / 有数据。

## 前置（只需做一次，换机器或重置后重做）

```bash
# 1. CLI 已登录
railway whoami

# 2. 每个子目录 link 到项目 + 对应 service（关键：必须在子目录内 link）
cd ~/WorkSpace/vibe_gaming_solo/gxq/polyEdge/backend
railway link -p 185f2839-ebec-4085-acab-beec770151f1 -e production -s backend

cd ~/WorkSpace/vibe_gaming_solo/gxq/polyEdge/frontend
railway link -p 185f2839-ebec-4085-acab-beec770151f1 -e production -s frontend
```

## 关键约定（踩坑记录，别踩第二次）

1. **必须在 `backend/`、`frontend/` 子目录内 `up`**。`railway.toml`（`builder=DOCKERFILE`）在子目录里，只有以子目录为根 up，Railway 才会用 Dockerfile 构建；在上层 `gxq/polyEdge/` 目录 up 会把整个仓上传，根目录没有 `railway.toml`，Railway 退回 Railpack 自动探测 → **构建失败**。

2. **前端 nginx 代理到后端公网必须开 SNI**。`frontend/nginx.conf` 的 `/api/`、`/uploads/` 代理块需要：
   - `proxy_ssl_server_name on;`（发送 TLS SNI，Railway edge 靠它路由）
   - **不要**写 `proxy_set_header Host $host;`（会把 Host 设成前端域名，Railway edge 路由不到后端 → 502 + 端口耗尽）；去掉后 nginx 默认用上游 backend 域名作 Host，即正确。

3. **端口不要写死**。`backend` 的 uvicorn 用 `--port ${PORT:-8000}`、`frontend` 的 nginx `listen ${PORT}`，都读 Railway 注入的 `PORT`；**不要**在变量里设 `PORT`。

## 环境变量清单

后端（`backend` service）：

```env
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
SECRET_KEY=<强随机值，勿泄露>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
MARKET_PREFETCH_INTERVAL_SECONDS=30
MARKET_PREFETCH_BATCH_LIMIT=100
MARKET_REFRESH_THROTTLE_SECONDS=30
EVENT_LIST_PAGE_SIZE=20
RANKING_TOP_N=10
EVENT_SEARCH_LIMIT=10
REALTIME_RATE_LIMIT_WINDOW=60
REALTIME_RATE_LIMIT_MAX=30
```

前端（`frontend` service）：

```env
BACKEND_UPSTREAM=https://backend-production-c92fb.up.railway.app
```

## 常用运维命令

```bash
# 部署/服务状态（先 cd 到对应目录，或用 -s 指定）
railway status

# 构建日志 / 运行日志
railway logs -s backend --build
railway logs -s backend -d

# 查看 / 设置变量
railway variables -s backend --kv
railway variables -s backend --set 'K=V'

# 生成域名
railway domain -s backend
```

## 若以后想改为 GitHub 自动部署

当前几个 service 是 CLI 直推的，`nginx.conf` 的 SNI 修复只在本地副本里。要改走 push 自动部署：

1. 把本地 `gxq/polyEdge/frontend/nginx.conf` 的 SNI 修复**提交推送**到 `HiGoalAI/vibe_gaming_solo`（否则从 git 构建会退回坏版本）。
2. 在 Railway 面板给 `backend`、`frontend` service 连接 GitHub 仓库 `HiGoalAI/vibe_gaming_solo`，Root Directory 分别设 `gxq/polyEdge/backend`、`gxq/polyEdge/frontend`。
3. 之后 `git push` 即自动部署，不再需要 `railway up`。
