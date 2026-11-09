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
