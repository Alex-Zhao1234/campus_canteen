# 校园食堂点评推荐系统

面向大学生的食堂**菜品级**点评与推荐工具。核心取向：**避雷优先、5 秒评价、天级时效**。

**在线演示：https://campus-canteen-34yw.onrender.com** （Render 免费托管，闲置后首次打开约需 1 分钟唤醒；登录页输入任意 `xxx@xxx.edu.cn` 邮箱按回车即可进入。）仓库：https://github.com/Alex-Zhao1234/campus_canteen 。完整架构见 `docs/架构设计.md`，项目介绍页见 https://claude.ai/artifact/9oBEZPyiWA3QHYsiHH4mdt （源码 `docs/showcase/index.html`）。

## 现状

MVP 四件事前后端均已完成，本地可跑：

| 功能 | 后端 | 前端 |
|---|---|---|
| 窗口列表 | `GET /canteens` · `/canteens/{id}/stalls` · `/stalls/{id}` · `/dishes/{id}` | 首页食堂切换、食堂页按楼层分组、窗口页、菜品页 |
| 一键评价 | `POST /reviews` · `DELETE /reviews/{id}` · `GET /me/reviews` · `GET /tags` | `RatingQuickBar`：表情三选一 → 3 秒内补标签 → 乐观更新 |
| 今日榜单 | 定时任务每 10 分钟写 `ranking_snapshot`，`GET /rankings/today?type=good\|bad` | 好评榜 / 踩雷榜 Tab，名次变化箭头 |
| 随机推荐 | `GET /recommend/random?budget=&spicy=&veg=&canteen_id=&exclude=` | 浮动按钮 → 抽屉，约束 chip，换一个 |
| 登录 | `POST /auth/send-code` · `/auth/verify` · `/auth/refresh` · `GET /me` | 校园邮箱验证码（开发模式验证码直接回显） |

后端 117 个 pytest 用例全部通过；评分公式、时间衰减、榜单门槛等常量集中在 `backend/app/recommender/scoring.py`。

## 技术栈

- 后端：Python 3.12 · FastAPI · SQLAlchemy 2.0 async · aiosqlite · Alembic · APScheduler · Pydantic v2
- 前端：React 18 · TypeScript · Vite · TanStack Query（服务端状态）· Zustand（本地状态）· React Router
- 数据库：SQLite（WAL）。`review` 表是 append-only 事件流，所有聚合指标从事件派生，可随时重算。
- 第二阶段：sqlite-vec 向量检索（`EMBEDDING_BACKEND=none` 时全部跳过）

## 快速开始

### 方式一：Docker（推荐，一条命令）

需要 Docker Desktop（WSL 用户在 Settings → Resources → WSL integration 里勾选发行版）。

```bash
cp .env.example .env        # 按需改 SECRET_KEY；本地体验设 AUTH_CODE_REQUIRED=false 可免验证码登录
make up                     # 构建并后台启动，首次需要几分钟
```

打开 http://localhost 。容器启动时会自动迁移数据库并导入 `data/seed/dishes.csv`。`make logs` 看日志，`make down` 停止。

### 方式一点五：Render 免费托管（公网演示）

仓库根目录有 `render.yaml` 和单容器 `Dockerfile`。在 https://render.com 用 GitHub 登录 → New → Blueprint → 选本仓库 → Apply。免费实例 15 分钟无访问会休眠（冷启动约 1 分钟），磁盘不持久，重启后评价数据回到种子状态。

### 方式二：本地开发

```bash
./setup.sh                  # 装后端/前端依赖、生成 .env、执行迁移
make seed                   # 导入种子数据（幂等，可重复执行）
make dev-api                # 终端 1：后端  http://localhost:8000/docs
make dev-web                # 终端 2：前端  http://localhost:5173
```

登录时用任意 `xxx@xxx.edu.cn` 邮箱。`AUTH_CODE_REQUIRED=false` 时按回车直接登录；为 `true` 且 `AUTH_ECHO_CODE=true` 时验证码会直接填到页面上。

## 常用命令

| 命令 | 作用 |
|---|---|
| `make test` / `make lint` | 后端 pytest / ruff |
| `make migrate` | 升级数据库到最新迁移 |
| `make migration m="说明"` | 改了模型后生成迁移脚本 |
| `make seed` | 导入预设标签与菜品 CSV |
| `make rankings` | 手动重算 stats 并生成榜单快照 |
| `make up` / `make down` / `make logs` | Docker 整套起停 |
| `cd frontend && npx tsc -b && npm run build` | 前端类型检查与构建 |

## 配置（`.env`）

| 变量 | 说明 |
|---|---|
| `DATABASE_URL` | 默认 `sqlite+aiosqlite:///../data/canteen.db` |
| `SECRET_KEY` | JWT 签名密钥，**生产必改** |
| `ALLOWED_EMAIL_DOMAINS` | 允许登录的邮箱域名，逗号分隔 |
| `AUTH_CODE_REQUIRED` | `false` = 邮件服务关闭，输入校园邮箱按回车直接登录，不发验证码（内测/演示用，**身份未验证**）；接上邮件服务后改回 `true` |
| `AUTH_ECHO_CODE` | 需要验证码但没有邮件服务时的开发模式：验证码直接回传在接口响应里，**生产必须 false** |
| `SCHEDULER_ENABLED` / `RANKING_INTERVAL_MINUTES` | 榜单定时任务开关与间隔 |
| `WEB_PORT` | Docker 对外端口，默认 80 |

## 目录

```
backend/
  app/
    api/v1/        路由（只接参数、包响应壳）      api/deps.py 依赖注入链
    services/      业务规则与事务边界              repositories/  数据访问
    recommender/   scoring 常量、stats 派生、ranking 榜单、random_pick 抽样（纯函数）
    tasks/         seed 种子导入、rankings 榜单任务 core/scheduler.py APScheduler
    models/ schemas/ core/
  alembic/         迁移脚本                        tests/  pytest（内存 SQLite）
frontend/src/
  api/ types/ hooks/ stores/ components/ pages/
data/              SQLite 文件、种子 CSV、图片
docs/              架构设计文档、项目介绍页
```

## WSL 环境准备（首次）

```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip build-essential unzip
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash && source ~/.bashrc && nvm install 20
curl -LsSf https://astral.sh/uv/install.sh | sh          # 可选，更快的 Python 包管理
```

项目请放在 WSL 文件系统内（如 `~/projects/campus-canteen`），不要放在 `/mnt/c/` 下，否则文件监听和热更新会很慢。VS Code 装 **WSL** 扩展后在 WSL 终端 `code .` 打开。

## 路线

- **M1 · MVP（已完成开发）**：上面五项。验收标准：上线 2 周后目标食堂 60% 以上常驻菜品有 ≥ 3 条评价，日均评价 ≥ 100。
- **M2 · 深化**：踩雷预警（`stall_alert`）、价格追踪、菜品页评价流、混合搜索（sqlite-vec）。
- **M3 · 个性化**：协同过滤、评价语义聚合、新菜投稿。
- **M4 · 扩展**：多校区，迁移 PostgreSQL + pgvector。
