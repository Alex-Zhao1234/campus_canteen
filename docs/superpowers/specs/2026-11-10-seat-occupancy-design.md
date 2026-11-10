# 食堂空余座位 —— 设计说明

日期：2026-11-10　状态：已确认（对话中确认方案后落稿）

## 1. 目标

- 概念：每个座位下有压力/红外传感器，有人坐下即"占用"，状态经网关汇总到后端。**本期传感器与上报链路只做概念说明，不落码**（见第 4.1 节）。
- App 在「食堂列表页」下方新增「食堂空位」区块：每个食堂一张卡，按层显示 **占用率 + 拥挤度分层 + 剩余座位数**，5 秒内刷新。
- 没有真实硬件，内置模拟器扮演"网关"，按餐段曲线生成座位进出直接写库，演示环境可直接看到效果。

不做：传感器上报 HTTP 接口与设备鉴权、座位级点阵图、历史曲线、按窗口附近找座、管理端录入座位、`seat_event` 历史流（以后做"各时段拥挤曲线"时再加）。

## 2. 数据模型（新增 2 张表，1 次 Alembic 迁移）

`seat`（静态，种子导入）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | int PK | |
| canteen_id | FK canteen | |
| floor | int | 楼层，与 stall.floor 同口径 |
| code | str(30) unique | 传感器上报用的座位编码，如 `C2-1F-037` |
| is_active | bool | 拆除/维修的座位置 false，不计入总数 |

索引：`ix_seat_canteen_floor (canteen_id, floor)`。

`seat_state`（当前状态，由"读数来源"upsert：本期是模拟器，将来是传感器网关）

| 字段 | 类型 | 说明 |
|---|---|---|
| seat_id | FK seat PK | |
| is_occupied | bool | |
| changed_at | datetime UTC | 最近一次状态翻转时间 |
| updated_at | datetime UTC | 最近一次读数（心跳）时间 |

没有 `seat_state` 记录的座位视为空闲。每层人数不建表，查询时 `GROUP BY canteen_id, floor` 现算。

## 3. 拥挤度分层

常量集中在 `app/seating/levels.py`，纯函数 `level_for(occupied, total) -> Level`：

| level | 中文 | 占用率 ratio = occupied / total |
|---|---|---|
| unknown | 暂无数据 | total == 0 |
| empty | 空闲 | ratio < 0.25 |
| low | 较少 | 0.25 ≤ ratio < 0.50 |
| medium | 适中 | 0.50 ≤ ratio < 0.70 |
| high | 较多 | 0.70 ≤ ratio < 0.85 |
| full | 爆满 | ratio ≥ 0.85 |

理由：找座难度非线性。70% 以前随便坐；70%–85% 要绕一圈；85% 以上剩的是散落单座，体验等于满。所以高两档区间故意窄。

## 4. 接口

### 4.1 传感器接入（概念说明，本期不落码）

真实部署时的链路：

```
座位传感器（压力/红外，一座一个）
   → 楼层网关（LoRa/Zigbee 汇聚，去抖：状态持续 ≥ 10 秒才算翻转）
   → 后端上报接口（将来：POST /api/v1/sensors/seat-states，请求头 X-Sensor-Key 设备密钥）
   → SeatService.apply_states()  → upsert seat_state
```

- 座位编码 `seat.code`（如 `C2-1F-037`）就是传感器/网关侧配置的设备标识，两边靠它对上。
- 上报语义：按批给出若干 `{code, is_occupied, ts}` 读数；同批同 code 以最后一条为准；未知或停用的 code 跳过不整批失败；`is_occupied` 翻转时更新 `changed_at`，每次读数都更新 `updated_at`（心跳）。
- 本期**只实现**服务层入口 `SeatService.apply_states(readings, now)`（上面链路的最后一步），HTTP 接口、设备鉴权、去抖都不写代码。模拟器（第 5 节）直接调用该方法，扮演网关角色。将来接真硬件时只需加一个路由层文件调用同一个方法。

### 4.2 空位查询（登录用户）

`GET /api/v1/seats/occupancy?campus_id=`

返回所有在营食堂（`is_active`），按 `canteen.floors` 列出每一层（没有座位的层也出现，level=unknown）：

```json
[
  {
    "canteen_id": 1, "canteen_name": "二食堂", "floors": 3,
    "levels": [
      { "floor": 1, "total": 160, "occupied": 131, "free": 29,
        "ratio": 0.819, "level": "high", "updated_at": "2026-11-10T04:12:00Z" }
    ]
  }
]
```

`updated_at` 为该层所有座位 `seat_state.updated_at` 的最大值，没有则 null。`campus_id` 缺省返回全部校区。

## 5. 模拟器（内置假网关）

`app/tasks/seat_sim.py`，`simulate_tick(session, now)`：

1. 取北京时间的时刻，查目标占用率曲线（分段线性插值）：

| 北京时间 | 目标占用率 |
|---|---|
| 00:00–06:30 | 0.03 |
| 07:00–08:30 | 0.35（早餐小高峰） |
| 09:30–11:00 | 0.08 |
| 11:30–12:30 | 0.90（午高峰） |
| 13:30–16:30 | 0.08 |
| 17:30–18:30 | 0.85（晚高峰） |
| 20:00–23:59 | 0.05 |

   层间差异：1 层 ×1.0，2 层 ×0.9，3 层及以上 ×0.8，再加 ±0.05 随机噪声，夹到 [0, 0.98]。
2. 对每个食堂每层：当前占用数与目标差 `gap`，本 tick 翻转 `min(|gap|, max(1, total × 0.05))` 个随机座位（朝目标方向），并额外随机翻转 1% 座位模拟进出，让高峰时也有人起身。
3. 翻转结果走 `SeatService.apply_states`，将来真实传感器网关接入时走同一个方法。

调度：`core/scheduler.py` 增加 interval job，`SEAT_SIM_INTERVAL_SECONDS`（默认 5），开关 `SEAT_SIMULATOR_ENABLED`（默认 false；render.yaml 置 true；测试固定 false）。`make seat-sim` 手动跑一个 tick。

## 6. 种子

`data/seed/seats.csv`：

```
canteen_name,floor,seat_count
二食堂,1,160
二食堂,2,120
二食堂,3,80
三食堂,1,140
三食堂,2,100
```

`seed_seats(session, csv_path)`：按食堂名查 canteen（不存在则跳过并告警，依赖 dishes.csv 先导入），座位编码 `f"C{canteen.id}-{floor}F-{n:03d}"`，按 code get-or-create，幂等；`seat_count` 减少不删座位。`make seed` 与 `docker-entrypoint.sh` 在 dishes 之后调用。

## 7. 配置

`.env.example`、`core/config.py`、`render.yaml`、`docker-compose.yml`：

- `SEAT_SIMULATOR_ENABLED`（默认 false）
- `SEAT_SIM_INTERVAL_SECONDS`（默认 5）

## 8. 前端

- `types/api.ts`：`SeatLevel`、`FloorOccupancy`、`CanteenOccupancy`。
- `api/seats.ts`：`seatsApi.occupancy()`。
- `hooks/queries.ts`：`keys.seatOccupancy`，`useSeatOccupancy()`：`refetchInterval: 5000`，`refetchIntervalInBackground: false`。
- `components/SeatOccupancy.tsx`：区块标题「食堂空位」，每食堂一张卡（标题「二食堂 3层」），卡内每层一行：`1层　● 较多　剩 29 / 160` + 细进度条；颜色 token 按 level：empty/low 绿、medium 黄、high 橙、full 红、unknown 灰；卡右上「x 秒前更新」（取各层 updated_at 最大值，每秒重算文案）。
- `pages/Canteens.tsx`：在现有食堂列表下方挂 `<SeatOccupancy />`。加载中/失败不影响上方列表。
- 样式继续写在 `index.css`。

## 9. 测试

- `tests/test_seat_levels.py`：阈值边界（0.25/0.50/0.70/0.85 各边界、total=0）。
- `tests/test_seat_service.py`：`apply_states` 正常 upsert、未知/停用 code 进 unknown_codes、同批重复 code 取最后一条、`changed_at` 只在翻转时更新而 `updated_at` 每次更新。
- `tests/test_api_seats.py`：未登录 401、每层聚合数字与 level 正确、无座位层 unknown、停用座位不计、停用食堂不出现、campus_id 过滤。
- `tests/test_seat_sim.py`：目标曲线插值（午高峰 ≈0.9、凌晨 ≈0.03）、一个 tick 后占用数朝目标移动且不越界、走 apply_states。
- `tests/test_seed.py` 增加座位幂等用例。
- `tests/test_migrations.py` 现有校验覆盖新迁移。

## 10. 与架构文档的关系

`docs/架构设计.md` 第 5.2 节追加 `seat` / `seat_state`，第 6 节追加 `/seats/occupancy` 接口，第 7 章追加 7.6「座位拥挤度与传感器接入（概念）」把上面 4.1 的链路写进去并标明本期不落码；CLAUDE.md「当前状态」同步一条。
