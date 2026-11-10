/** 与后端 app/schemas/*.py 一一对应的类型。字段名保持 snake_case。 */

export interface Canteen {
  id: number;
  campus_id: number;
  name: string;
  floors: number;
}

export interface StallStats {
  score_7d: number;
  bad_count_24h: number;
  review_count_24h: number;
}

export interface DishStats {
  score_7d: number;
  good_rate_7d: number;
  review_count_7d: number;
  review_count_all: number;
}

export interface Stall {
  id: number;
  canteen_id: number;
  floor: number;
  name: string;
  cuisine_type: string | null;
  position_desc: string | null;
  today_status: "open" | "closed" | "unknown";
  stats: StallStats;
}

export interface Dish {
  id: number;
  stall_id: number;
  name: string;
  price_cents: number;
  spicy_level: number;
  is_veg: boolean;
  portion_hint: string | null;
  dish_type: string;
  /** 站内静态路径或外链，null 时显示占位 */
  image_url: string | null;
  stats: DishStats;
}

export interface StallDetail extends Stall {
  dishes: Dish[];
}

export interface DishDetail extends Dish {
  stall: {
    id: number;
    name: string;
    floor: number;
    canteen_id: number;
    canteen_name: string;
  };
}

export type RankingType = "good" | "bad";

export interface RankingItem {
  rank: number;
  dish_id: number;
  dish_name: string;
  stall_id: number;
  stall_name: string;
  canteen_id: number;
  canteen_name: string;
  price_cents: number;
  image_url: string | null;
  score: number;
  review_count_7d: number;
  delta: number | null;
}

export interface Ranking {
  ranking_type: RankingType;
  campus_id: number | null;
  canteen_id: number | null;
  generated_at: string | null;
  items: RankingItem[];
}

export interface User {
  id: number;
  campus_id: number;
  nickname: string;
  trust_score: number;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  user: User;
}

/* ---------- 认证 ---------- */

export interface SendCodeOut {
  sent: boolean;
  /** false：邮件服务关闭，直接调 verify（不带 code）即可登录 */
  code_required: boolean;
  /** 开发模式（AUTH_ECHO_CODE=true）后端直接回传验证码 */
  dev_code: string | null;
}

export interface AccessTokenOut {
  access_token: string;
  token_type: "bearer";
}

/* ---------- 评价 ---------- */

export type Verdict = "good" | "ok" | "bad";
export type MealSlot = "breakfast" | "lunch" | "dinner" | "night";

export interface Tag {
  code: string;
  label: string;
  category: string;
}

export interface ReviewCreateIn {
  dish_id: number;
  verdict: Verdict;
  tag_codes?: string[];
  comment?: string | null;
  meal_slot?: MealSlot | null;
}

export interface ReviewCreated {
  review_id: number;
  dish_id: number;
  dish_stats: DishStats;
}

export interface MyReview {
  id: number;
  dish_id: number;
  dish_name: string;
  stall_id: number;
  stall_name: string;
  verdict: Verdict;
  comment: string | null;
  meal_slot: MealSlot | null;
  tags: Tag[];
  created_at: string;
}

/** 菜品评论区的一条评价；comment 为 null 表示用户只点了表情没写字 */
export interface DishReview {
  id: number;
  user_nickname: string;
  verdict: Verdict;
  comment: string | null;
  tags: Tag[];
  created_at: string;
  is_mine: boolean;
}

export interface DishReviewPage {
  items: DishReview[];
  next_before_id: number | null;
}

/* ---------- 随机推荐 ---------- */

export interface RecommendItem {
  dish_id: number;
  dish_name: string;
  stall_id: number;
  stall_name: string;
  canteen_id: number;
  canteen_name: string;
  price_cents: number;
  spicy_level: number;
  is_veg: boolean;
  score_7d: number;
  review_count_7d: number;
}

export interface RandomRecommend {
  pick: RecommendItem | null;
  alternates: RecommendItem[];
  candidate_count: number;
}

export interface RecommendFilters {
  canteenId: number | null;
  /** 最高价（分），null 不限 */
  budget: number | null;
  /** 最高辣度 0-3，null 不限 */
  spicy: number | null;
  veg: boolean;
}

/* ---------- 座位空位 ---------- */

export type SeatLevel = "unknown" | "empty" | "low" | "medium" | "high" | "full";

export interface FloorOccupancy {
  floor: number;
  total: number;
  occupied: number;
  free: number;
  /** occupied / total，3 位小数；total 为 0 时 0 */
  ratio: number;
  level: SeatLevel;
  /** 该层最近一次读数（UTC naive），没有座位状态时 null */
  updated_at: string | null;
}

export interface CanteenOccupancy {
  canteen_id: number;
  canteen_name: string;
  floors: number;
  levels: FloorOccupancy[];
}
