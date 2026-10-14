"""围栏进出转换: 连续 3 点 + 持续 10 s 才切换."""
import pytest

from server import geofence as ge


SQUARE = {
    "type": "Polygon",
    "coordinates": [[
        [113.0, 22.0], [113.02, 22.0], [113.02, 22.02], [113.0, 22.02], [113.0, 22.0],
    ]],
}

INSIDE = (22.01, 113.01)
OUTSIDE = (22.05, 113.05)

S = 1000  # ms


@pytest.fixture
def fence():
    return ge.build_geofence(SQUARE, fence_id=1, name="厂区")


def feed(h, fence, point, t, accuracy=None):
    return h.feed(fence, point[0], point[1], t, accuracy=accuracy)


def test_first_point_only_seeds_state(fence):
    h = ge.FenceHysteresis()
    assert feed(h, fence, OUTSIDE, 0) is None
    assert h.state == ge.FENCE_STATE_OUTSIDE


def test_enter_needs_three_points_and_ten_seconds(fence):
    h = ge.FenceHysteresis()
    feed(h, fence, OUTSIDE, 0)                       # 初始状态: 外
    assert feed(h, fence, INSIDE, 1 * S) is None     # 1/3
    assert feed(h, fence, INSIDE, 5 * S) is None     # 2/3
    # 第 3 点但只过了 6 s, 时长不够.
    assert feed(h, fence, INSIDE, 7 * S) is None
    assert h.state == ge.FENCE_STATE_OUTSIDE
    # 再来一点, 距离 pending 起点已 12 s.
    assert feed(h, fence, INSIDE, 13 * S) == ge.TRANSITION_ENTER
    assert h.state == ge.FENCE_STATE_INSIDE


def test_three_points_within_ten_seconds_do_not_switch(fence):
    """点数够但时长不够, 不切换."""
    h = ge.FenceHysteresis()
    feed(h, fence, OUTSIDE, 0)
    for t in (1 * S, 2 * S, 3 * S, 4 * S):
        assert feed(h, fence, INSIDE, t) is None
    assert h.state == ge.FENCE_STATE_OUTSIDE


def test_long_wait_with_two_points_does_not_switch(fence):
    """时长够但点数不够, 不切换."""
    h = ge.FenceHysteresis()
    feed(h, fence, OUTSIDE, 0)
    assert feed(h, fence, INSIDE, 1 * S) is None
    assert feed(h, fence, INSIDE, 60 * S) is None
    assert h.state == ge.FENCE_STATE_OUTSIDE


def test_pending_resets_when_returning_to_current_state(fence):
    """门口来回: 攒到一半又跑回来, 计数清零, 不产生转换."""
    h = ge.FenceHysteresis()
    feed(h, fence, OUTSIDE, 0)
    feed(h, fence, INSIDE, 1 * S)
    feed(h, fence, INSIDE, 5 * S)
    assert feed(h, fence, OUTSIDE, 9 * S) is None   # 回到外, pending 清零
    assert feed(h, fence, INSIDE, 12 * S) is None   # 重新计数 1/3
    assert feed(h, fence, INSIDE, 15 * S) is None
    assert h.state == ge.FENCE_STATE_OUTSIDE


def test_exit_transition(fence):
    h = ge.FenceHysteresis()
    feed(h, fence, INSIDE, 0)
    feed(h, fence, OUTSIDE, 1 * S)
    feed(h, fence, OUTSIDE, 6 * S)
    assert feed(h, fence, OUTSIDE, 12 * S) == ge.TRANSITION_EXIT
    assert h.state == ge.FENCE_STATE_OUTSIDE


def test_accuracy_gate_drops_bad_fixes(fence):
    h = ge.FenceHysteresis()
    feed(h, fence, OUTSIDE, 0)
    for t in (1 * S, 6 * S, 12 * S, 18 * S):
        assert feed(h, fence, INSIDE, t, accuracy=200.0) is None
    assert h.state == ge.FENCE_STATE_OUTSIDE


def test_null_accuracy_passes_the_gate(fence):
    """accuracy 为 None 视为通过门槛 (设备测点里没有精度)."""
    h = ge.FenceHysteresis()
    feed(h, fence, OUTSIDE, 0, accuracy=None)
    feed(h, fence, INSIDE, 1 * S, accuracy=None)
    feed(h, fence, INSIDE, 6 * S, accuracy=None)
    assert feed(h, fence, INSIDE, 12 * S, accuracy=None) == ge.TRANSITION_ENTER


def test_accuracy_buffer_band_keeps_state(fence):
    """点离边界比定位误差还近时不推进 pending."""
    h = ge.FenceHysteresis()
    feed(h, fence, OUTSIDE, 0, accuracy=5.0)
    near_boundary = (22.02001, 113.01)  # 距上边界约 1 m
    for t in (1 * S, 6 * S, 12 * S, 18 * S):
        assert feed(h, fence, near_boundary, t, accuracy=20.0) is None
    assert h.state == ge.FENCE_STATE_OUTSIDE


def test_transition_matches():
    assert ge.transition_matches("both", ge.TRANSITION_ENTER) is True
    assert ge.transition_matches("both", ge.TRANSITION_EXIT) is True
    assert ge.transition_matches(None, ge.TRANSITION_EXIT) is True
    assert ge.transition_matches("enter", ge.TRANSITION_ENTER) is True
    assert ge.transition_matches("enter", ge.TRANSITION_EXIT) is False
    assert ge.transition_matches("exit", ge.TRANSITION_ENTER) is False
