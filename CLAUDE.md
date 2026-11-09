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
- 已有：最简认证 `POST /auth/send-code` / `verify` / `refresh` 与 `GET /me`。邮箱验证码登录，验证码存进程内 `CodeStore`（10 分钟、限错 5 次、一次性），开发模式 `AUTH_ECHO_CODE=true` 把验证码回传在响应里（无邮件服务）。JWT 在 `core/security.py`，access/refresh 用 `type` 字段区分不可互用；首次登录按 `sha256(邮箱)` 自动建用户、校区取第一个。需登录的路由写 `user: CurrentUser`（`api/deps.py`），未登录/无效 token 统一 401 壳。
- 已有：一键评价 `POST /reviews`（201）、`DELETE /reviews/{id}`（软删 is_hidden）、`GET /me/reviews`、`GET /tags`。规则：菜品需在售（404）、标签 code 需存在（400）、单人单菜单日一评由唯一索引保证、服务层把 `IntegrityError` 翻译成 409、单日上限 15 条（429）。写入后就地重算该菜/该窗口的 stats：`app/recommender/stats.py` 纯函数（`compute_dish_metrics` / `compute_stall_metrics`，隐藏评价不计），榜单任务要复用它，不要再写一套公式。
- 注意：`review.created_at` 存 UTC，"一天"按北京日切（索引 `date(created_at, '+8 hours')`，迁移 b2c3d4e5f6a7；服务层 `beijing_day_start_utc`）。
- 下一步：榜单任务（APScheduler 每 10 分钟写 `ranking_snapshot`，`GET /rankings/today`）→ 随机推荐 `GET /recommend/random` → 前端页面。
