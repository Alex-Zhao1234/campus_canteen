"""拥挤度分层阈值（spec 第 3 节）：边界值落在上一档还是下一档必须固定。"""

import pytest

from app.seating.levels import LEVEL_LABELS, level_for, occupancy_ratio


@pytest.mark.parametrize(
    ("occupied", "total", "expected"),
    [
        (0, 0, "unknown"),
        (5, 0, "unknown"),
        (0, 100, "empty"),
        (24, 100, "empty"),
        (25, 100, "low"),
        (49, 100, "low"),
        (50, 100, "medium"),
        (69, 100, "medium"),
        (70, 100, "high"),
        (84, 100, "high"),
        (85, 100, "full"),
        (100, 100, "full"),
        (3, 4, "high"),  # 0.75
    ],
)
def test_level_boundaries(occupied, total, expected):
    assert level_for(occupied, total) == expected


def test_ratio_rounds_to_three_places_and_handles_zero_total():
    assert occupancy_ratio(0, 0) == 0.0
    assert occupancy_ratio(1, 3) == 0.333
    assert occupancy_ratio(160, 160) == 1.0


def test_every_level_has_chinese_label():
    assert LEVEL_LABELS == {
        "unknown": "暂无数据",
        "empty": "空闲",
        "low": "较少",
        "medium": "适中",
        "high": "较多",
        "full": "爆满",
    }
