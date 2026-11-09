"""从维基共享资源（Wikimedia Commons）为种子菜品抓取自由许可的图片。

开发期一次性脚本：按菜名依次尝试若干搜索词，取第一张 jpeg/png、许可为 CC0 / CC BY / CC BY-SA / 公有领域
的图，下载 640px 缩略图到 frontend/public/dish-images/<slug>.jpg，写 CREDITS.md 署名，
并把 /dish-images/<slug>.jpg 写回 data/seed/dishes.csv 的 image_url 列。
用法：python3 scripts/fetch_dish_images.py
"""

import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "public" / "dish-images"
CSV = ROOT / "data" / "seed" / "dishes.csv"
UA = "campus-canteen-demo/0.1 (student project; contact via GitHub Alex-Zhao1234/campus_canteen)"
ALLOWED = ("cc0", "cc by", "cc-by", "public domain", "pd")

# 菜名 → (slug, [搜索词...])，搜索词按优先级排列，前面搜不到就用后面更泛的替代
DISHES: dict[str, tuple[str, list[str]]] = {
    "豆浆": ("doujiang", ["soy milk glass", "soy milk"]),
    "肉包": ("roubao", ["baozi steamed bun", "baozi"]),
    "油条": ("youtiao", ["youtiao", "fried dough stick"]),
    "茶叶蛋": ("chayedan", ["tea egg", "chinese tea eggs"]),
    "小米粥": ("xiaomizhou", ["millet congee", "millet porridge"]),
    "牛肉面": ("niuroumian", ["Lanzhou beef noodle soup", "beef noodle soup"]),
    "刀削面": ("daoxiaomian", ["daoxiaomian", "knife-cut noodles"]),
    "炸酱面": ("zhajiangmian", ["zhajiangmian", "zha jiang mian"]),
    "麻辣烫(自选)": ("malatang", ["malatang", "mala tang"]),
    "冒菜": ("maocai", ["malatang bowl", "mala tang soup bowl", "spicy beef soup bowl Sichuan", "Chongqing spicy noodle soup"]),
    "番茄炒蛋": ("fanqiechaodan", ["stir-fried tomato and scrambled eggs", "tomato egg stir fry"]),
    "鱼香肉丝": ("yuxiangrousi", ["Yuxiang rousi", "fish-fragrant shredded pork", "Yu Xiang Rou Si", "shredded pork garlic sauce"]),
    "宫保鸡丁": ("gongbaojiding", ["Kung Pao chicken", "Gong Bao chicken", "kung po chicken"]),
    "酸辣土豆丝": ("suanlatudousi", ["suan la tu dou si", "shredded potato stir fry", "tudousi"]),
    "红烧肉": ("hongshaorou", ["hong shao rou", "red braised pork belly"]),
    "咖喱鸡排饭": ("galijipaifan", ["chicken katsu curry", "katsu curry rice"]),
    "回锅肉盖饭": ("huiguorou", ["twice cooked pork", "hui guo rou"]),
    "青椒肉丝盖饭": ("qingjiaorousi", ["qing jiao rou si", "shredded pork with green pepper", "pepper pork stir fry"]),
    "叉烧饭": ("chashaofan", ["char siu rice", "char siu"]),
    "烧鸭饭": ("shaoyafan", ["roast duck rice", "cantonese roast duck"]),
    "白切鸡饭": ("baiqiejifan", ["white cut chicken", "Hainanese chicken rice"]),
    "麻辣香锅(荤)": ("malaxiangguo", ["Mala xiangguo", "Mala Xiang Guo", "Sichuan dry pot", "spicy dry pot stir fry"]),
    "麻辣香锅(素)": ("malaxiangguo-su", ["dry pot cauliflower", "stir fried lotus root chili", "Sichuan stir-fried vegetables", "stir-fried mixed vegetables chili"]),
    "铁板牛肉饭": ("tiebanniurou", ["sizzling beef plate", "teppanyaki beef", "iron plate beef"]),
    "铁板鱿鱼": ("tiebanyouyu", ["grilled squid", "teppanyaki squid"]),
    "羊肉泡馍": ("yangroupaomo", ["yangrou paomo", "paomo"]),
    "肉夹馍": ("roujiamo", ["Roujiamo meat bun", "Chinese hamburger pork bun Xi'an", "roujiamo pork", "roujiamo"]),
    "凉皮": ("liangpi", ["liangpi", "liang pi noodles"]),
    "石锅拌饭": ("shiguobanfan", ["dolsot bibimbap", "bibimbap"]),
    "部队锅": ("buduiguo", ["budae jjigae", "army stew korean"]),
    "鸡胸肉沙拉": ("jixiongroushala", ["grilled chicken salad", "chicken salad bowl"]),
    "牛油果沙拉": ("niuyouguoshala", ["avocado salad bowl", "avocado tomato salad plate", "salad with avocado slices"]),
    "剁椒鱼头": ("duojiaoyutou", ["duojiao yutou", "steamed fish head with chopped chili"]),
    "小炒黄牛肉": ("xiaochaohuangniurou", ["Hunan beef", "stir-fried beef with chili peppers", "Hunan cuisine beef", "beef with green peppers stir fry"]),
    "农家小炒肉": ("nongjiaxiaochaorou", ["nongjia xiaochao rou", "Hunan stir fried pork with chili", "xiao chao rou"]),
    "锅包肉": ("guobaorou", ["guobaorou", "guo bao rou"]),
    "地三鲜": ("disanxian", ["di san xian", "disanxian"]),
    "酸菜白肉": ("suancaibairou", ["suancai bairou", "pork with pickled cabbage", "suan cai bai rou"]),
}


def api(params: dict) -> dict:
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({**params, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def search(term: str) -> dict | None:
    data = api({
        "action": "query", "generator": "search", "gsrsearch": term, "gsrnamespace": 6, "gsrlimit": 8,
        "prop": "imageinfo", "iiprop": "url|extmetadata|mime|size", "iiurlwidth": 640,
    })
    pages = data.get("query", {}).get("pages", {})
    # 搜索结果带 index 字段表示相关度顺序
    for p in sorted(pages.values(), key=lambda x: x.get("index", 99)):
        ii = p.get("imageinfo", [{}])[0]
        md = ii.get("extmetadata", {})
        lic = md.get("LicenseShortName", {}).get("value", "").lower()
        if ii.get("mime") not in ("image/jpeg", "image/png"):
            continue
        if not any(lic.startswith(a) for a in ALLOWED):
            continue
        if ii.get("width", 0) < 400:
            continue
        return {
            "title": p["title"], "thumb": ii["thumburl"], "page": ii["descriptionurl"],
            "license": md.get("LicenseShortName", {}).get("value", ""),
            "author": _strip(md.get("Artist", {}).get("value", "")),
        }
    return None


def _strip(html: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", html).strip()[:80] or "unknown"


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r, dest.open("wb") as f:
        f.write(r.read())


def main() -> None:
    only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
    pause = float(sys.argv[sys.argv.index("--sleep") + 1]) if "--sleep" in sys.argv else 0.4
    OUT.mkdir(parents=True, exist_ok=True)
    credits = ["# 菜品图片来源\n", "\n", "全部来自 Wikimedia Commons，自由许可，仅作演示。\n", "\n",
               "| 菜品 | 文件 | 作者 | 许可 | 来源 |\n", "|---|---|---|---|---|\n"]
    found: dict[str, str] = {}
    for name, (slug, terms) in DISHES.items():
        if only and name not in only:
            continue
        dest = OUT / f"{slug}.jpg"
        hit = None
        used = None
        for t in terms:
            try:
                hit = search(t)
            except Exception as e:  # noqa: BLE001
                print(f"  ! {name} 搜索 {t!r} 出错：{e}", file=sys.stderr)
                hit = None
            if hit:
                used = t
                break
            time.sleep(pause)
        if not hit:
            print(f"✗ {name}: 没搜到可用图片")
            continue
        try:
            download(hit["thumb"], dest)
        except Exception as e:  # noqa: BLE001
            print(f"✗ {name}: 下载失败 {e}")
            continue
        found[name] = f"/dish-images/{slug}.jpg"
        credits.append(f"| {name} | `{slug}.jpg` | {hit['author']} | {hit['license']} | [{hit['title']}]({hit['page']}) |\n")
        print(f"✓ {name:8s} ← {used!r:40s} {hit['license']:12s} {dest.stat().st_size // 1024} KB")
        time.sleep(pause)

    credits_path = OUT / "CREDITS.md"
    if only and credits_path.exists():
        credits_path.write_text(credits_path.read_text(encoding="utf-8") + "".join(credits[6:]), encoding="utf-8")
    else:
        credits_path.write_text("".join(credits), encoding="utf-8")

    # 写回 CSV 的 image_url 列
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    fields = list(rows[0].keys())
    if "image_url" not in fields:
        fields.append("image_url")
    for r in rows:
        r["image_url"] = found.get(r["dish_name"], r.get("image_url", "") or "")
    with CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"\n完成：{len(found)}/{len(DISHES)} 道菜有图，CSV 已更新")


if __name__ == "__main__":
    main()
