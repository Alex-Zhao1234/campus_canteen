"""应用启动时 create_all 必须覆盖全部模型：app.main 自身要确保模型已注册到 Base.metadata。"""

import subprocess
import sys

EXPECTED_TABLES = {
    "campus", "canteen", "stall", "dish",
    "user",
    "review", "tag", "review_tag",
    "dish_stats", "stall_stats", "ranking_snapshot",
}


def test_importing_app_main_registers_all_tables():
    code = (
        "import app.main; from app.core.database import Base; "
        "print(','.join(sorted(Base.metadata.tables)))"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert set(out.stdout.strip().split(",")) == EXPECTED_TABLES
