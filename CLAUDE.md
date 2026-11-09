# 项目：校园食堂点评推荐系统

## 一句话
面向大学生的食堂菜品级点评 + 推荐工具，核心是"避雷优先、5 秒评价、天级时效"。

## 必读
- `docs/架构设计.md` —— 完整架构、数据模型、API、评分公式、迭代路线。动手前先读对应章节。
- MVP 只做四件事：窗口列表、一键评价、今日榜单（好评/踩雷）、随机推荐。不要擅自扩 scope。

## 技术栈与约定
- 后端 Python 3.11+，FastAPI + SQLAlchemy 2.0 async + aiosqlite + Pydantic v2。分层：api → services → repositories → models，路由层不写业务逻辑。
- 前端 React 18 + TS + Vite，TanStack Query 管服务端状态，Zustand 管本地状态。
- 数据库 SQLite（WAL）。向量检索（sqlite-vec）是第二阶段，`EMBEDDING_BACKEND=none` 时所有向量相关代码必须可跳过。
- 评价表 `review` 是 append-only 事件流，聚合指标全部派生，不要在 review 上做 UPDATE（软删除 is_hidden 除外）。
- 评分公式、时间衰减、预警阈值以 `docs/架构设计.md` 第 7 章为准，常量集中放 `app/recommender/scoring.py`。
- 中文注释、中文提交信息均可；接口字段用英文 snake_case。

## 常用命令
- `make dev-api` / `make dev-web` / `make test` / `make lint` / `make seed`
- 后端测试用 pytest + httpx AsyncClient，测试库用内存 SQLite。

## 当前状态
- 已有：架构文档、项目骨架、`/api/v1/health`、前端空壳页、项目介绍页（`docs/showcase/`）。
- 已有：MVP 所需 11 张表的 ORM 模型（`app/models/`：org / user / review / stats），测试用内存 SQLite（`tests/conftest.py` 的 `db` / `client` fixture）。M2+ 的表（price_history、review_image、stall_alert、user_dish_pref、向量表）尚未建。
- 已有：Alembic 迁移（`backend/alembic/`），表结构不再由 create_all 建，启动前 `make migrate`。改模型后 `make migration m="说明"` 生成脚本，注意 autogenerate 识别不了函数索引 `uq_review_daily`，不要在新迁移里误删；`tests/test_migrations.py` 会校验迁移与模型一致。
- 已有：种子导入（`app/tasks/seed.py`，`make seed`）：附录 A 的 14 个预设标签 + 附录 B 格式的 CSV 按名字 get-or-create 校区/食堂/窗口/菜品，幂等可重复执行。
- 已有：组织结构只读接口 `GET /canteens`、`/canteens/{id}/stalls`、`/stalls/{id}`、`/dishes/{id}`，分层 api(`api/v1/*.py`) → services(`org_service.py`) → repositories(`org_repo.py`)；依赖注入用 `Annotated` 风格（`app/api/deps.py` 的 `OrgServiceDep`）；响应壳 `schemas/common.py` 的 `Envelope`/`ok`，业务异常 `services/errors.py` 由 `api/errors.py` 统一转成壳（404/422 也是壳）。列表接口只返回 is_active 的记录，stats 缺失时给全零。
- 已有：最简认证 `POST /auth/send-code` / `verify` / `refresh` 与 `GET /me`。`AUTH_CODE_REQUIRED=false` 时为"邮件服务关闭"模式：send-code 返回 `code_required: false`，verify 不带 code 直接登录（仍校验域名），前端登录页据此按一次回车即登录；本地 `.env` 与 docker 默认走此模式，接上邮件后改回 true。邮箱验证码登录，验证码存进程内 `CodeStore`（10 分钟、限错 5 次、一次性），开发模式 `AUTH_ECHO_CODE=true` 把验证码回传在响应里（无邮件服务）。JWT 在 `core/security.py`，access/refresh 用 `type` 字段区分不可互用；首次登录按 `sha256(邮箱)` 自动建用户、校区取第一个。需登录的路由写 `user: CurrentUser`（`api/deps.py`），未登录/无效 token 统一 401 壳。
- 已有：一键评价 `POST /reviews`（201）、`DELETE /reviews/{id}`（软删 is_hidden）、`GET /me/reviews`、`GET /tags`。规则：菜品需在售（404）、标签 code 需存在（400）、单人单菜单日一评由唯一索引保证、服务层把 `IntegrityError` 翻译成 409、单日上限 15 条（429）。写入后就地重算该菜/该窗口的 stats：`app/recommender/stats.py` 纯函数（`compute_dish_metrics` / `compute_stall_metrics`，隐藏评价不计），榜单任务要复用它，不要再写一套公式。
- 注意：`review.created_at` 存 UTC，"一天"按北京日切（索引 `date(created_at, '+8 hours')`，迁移 b2c3d4e5f6a7；服务层 `beijing_day_start_utc`）。
- 已有：榜单任务 `app/tasks/rankings.py` 的 `rebuild_rankings(session)`：全量重算在售菜/在营窗口的 stats（时间衰减靠它生效）→ 每个校区 × (全部食堂 + 每个食堂) 生成 good/bad 快照写 `ranking_snapshot`，同一维度只留最新一份，`delta` 对比上一份。纯函数在 `recommender/ranking.py`（好评榜只收正分、踩雷榜 < −0.3、冷启动门槛 1 条、每榜 20 条，常量在 `scoring.py`）。调度在 `core/scheduler.py`（APScheduler，lifespan 启停，启动即跑一次，`SCHEDULER_ENABLED` / `RANKING_INTERVAL_MINUTES`），手动 `make rankings`。`GET /rankings/today?type=good|bad&canteen_id=&campus_id=` 只读快照并关联菜名/窗口名，无快照返回空列表。餐段维度、新菜榜、上升榜未做。
- 已有：随机推荐 `GET /recommend/random?canteen_id=&campus_id=&budget=&spicy=&veg=&exclude=1,2`：硬约束过滤 → 排除黄牌窗口（`stall_stats` 现算 7.3 条件，`stall_alert` 表未建）与 `score_7d < −0.3` 的菜 → 登录用户再排除近 3 天评过的 → `softmax(score_7d/0.5)` 不放回抽 1 主推 + 2 备选；无候选返回 `pick: null`。纯函数 `recommender/random_pick.py`，常量在 `scoring.py`。公开接口的可选登录用 `user: OptionalUser`（无效 token 按游客）。
- **MVP 后端四件事接口已齐**（窗口列表 / 一键评价 / 今日榜单 / 随机推荐）。
- 已有：前端浏览链路（只读）。`src/types/api.ts` 与后端 schema 一一对应；`src/api/` 按资源封装，`client.ts` 自动带 token、401 时清登录态；服务端状态全走 `src/hooks/queries.ts`（queryKey 集中在 `keys`，评价提交后按键 invalidate）；本地状态 `src/stores/auth.ts`（persist）/ `ui.ts`（当前食堂）。页面：`/` 榜单（食堂 chips + 好评/踩雷 Tab）、`/canteens`、`/canteen/:id`（按楼层分组）、`/stall/:id`（菜品卡片，评价组件留位）、`/dish/:id`、`/me` 占位；`Layout` 顶栏 + 底部三 Tab；`ScoreBadge` 统一分数展示。`@/` 别名在 tsconfig 与 vite.config 两处。样式只用 `index.css`，无 UI 库，无 ESLint 依赖。
- 已有：前端登录（`/login`，邮箱验证码，开发模式自动填入 `dev_code`，`?next=` 回跳）与一键评价 `components/RatingQuickBar.tsx`。状态机 idle → tagging(3 秒倒计时，最多 3 标签，点标签重置) → submitting → done；**取舍：表情点击只高亮，请求在标签窗口结束时一次性发出**（保持 review append-only，不需要 PATCH）。`hooks/useSubmitReview.ts` 乐观 +1 评价数 → 成功后用响应里的 `dish_stats` 覆盖 → settled 失效 stall/dish/rankings/myReviews。409 置 done 并提示；401 跳登录。全局提示 `stores/toast.ts` + `components/Toaster.tsx`。已嵌入窗口页每张菜品卡与菜品详情页。
- 已有：随机推荐 `components/RandomPicker.tsx`（首页浮动按钮 → 底部抽屉；食堂/预算/辣度/素食 chip 存 `useUiStore` 持久化；`hooks/useRandomPick.ts` 不走缓存，`exclude` 累积已看过的 id，候选用尽清空重来）；我的评价（`/me`，`hooks/useMyReviews.ts` 列表 + 删除 mutation，乐观移除、settled 失效 stall/dish/rankings）。
- **MVP 前后端四件事全部完成**。
- 已有：Docker 化——`backend/Dockerfile`（python:3.12-slim + uv，`docker-entrypoint.sh` 先 migrate 再幂等 seed 再 uvicorn）、`frontend/Dockerfile`（多阶段：node 构建 → nginx 托管，`nginx.conf` 反代 `/api/` 到 `api:8000` + SPA 回退）、根目录 `docker-compose.yml`（api + web，`./data` 挂载到 `/app/data`，变量读根目录 `.env`），`make up/down/logs`。2026-11-09 已在 WSL + Docker Desktop 实际构建并跑通（api 484MB / web 94MB，首次构建约 10 分钟主要花在拉基础镜像与 uv/npm 下载）。本地 `.env` 里 `AUTH_ECHO_CODE=true`、`WEB_PORT=8080`。README 已重写。
- 已有：单容器部署（Render 免费托管用）：根目录 `Dockerfile` 先构建前端再拷进 Python 镜像，`STATIC_DIR` 非空时 `core/static.py` 由 FastAPI 托管静态文件 + SPA 回退（挂在 api_router 之后）；`docker-entrypoint.sh` 监听 `${PORT:-8000}`；`render.yaml` 蓝图（free 计划、新加坡区、演示模式 `AUTH_CODE_REQUIRED=false`）。免费实例会休眠且磁盘不持久。**线上演示地址：https://campus-canteen-34yw.onrender.com**（Render 服务名 campus-canteen，推 main 自动部署）。测试用 `conftest._pinned_settings` 固定认证开关，不受本地 `.env` 影响。
- 下一步：进入 M2——踩雷预警（`stall_alert` 表 + `AlertService` + `GET /alerts/active` + 首页横幅）→ 价格历史 → 菜品页评价流 → 混合搜索。
