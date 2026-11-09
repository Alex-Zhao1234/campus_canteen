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
- 下一步：一键评价接口（`POST /reviews`，需要先有最简用户/鉴权）→ 榜单任务 → 随机推荐。
