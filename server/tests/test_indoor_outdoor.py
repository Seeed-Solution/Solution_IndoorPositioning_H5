"""室内外迟滞状态机."""
import pytest

from server.handler import indoor_outdoor as io

S = 1000


@pytest.fixture(autouse=True)
def reset_state_machine():
    io.state_machine.reset()
    io.configure(**vars(io.HysteresisConfig()))
    yield
    io.state_machine.reset()
    io.configure(**vars(io.HysteresisConfig()))


def test_defaults_match_spec():
    cfg = io.get_config()
    assert cfg.outdoor_window_ms == 20_000
    assert cfg.outdoor_fix_count == 3
    assert cfg.outdoor_accuracy_max_m == 25.0
    assert cfg.outdoor_ble_quiet_ms == 15_000
    assert cfg.indoor_window_ms == 10_000
    assert cfg.indoor_sample_count == 2
    assert cfg.indoor_min_beacons == 2


def test_three_good_fixes_without_ble_go_outdoor():
    sm = io.state_machine
    assert sm.update("A", 0, True, 10.0, 0) is None
    assert sm.update("A", 5 * S, True, 10.0, 0) is None
    assert sm.update("A", 10 * S, True, 10.0, 0) == io.MODE_OUTDOOR


def test_fixes_outside_the_window_do_not_accumulate():
    sm = io.state_machine
    sm.update("A", 0, True, 10.0, 0)
    sm.update("A", 30 * S, True, 10.0, 0)      # 第 1 个已经滑出 20 s 窗口
    assert sm.update("A", 35 * S, True, 10.0, 0) is None


def test_low_accuracy_fixes_are_rejected():
    sm = io.state_machine
    for t in (0, 5 * S, 10 * S, 15 * S):
        assert sm.update("A", t, True, 80.0, 0) is None


def test_null_accuracy_passes_and_goes_outdoor():
    sm = io.state_machine
    sm.update("A", 0, True, None, 0)
    sm.update("A", 5 * S, True, None, 0)
    assert sm.update("A", 10 * S, True, None, 0) == io.MODE_OUTDOOR


def test_recent_ble_blocks_outdoor():
    """15 s 内看到过已配置信标就不能判室外."""
    sm = io.state_machine
    sm.update("A", 0, False, None, 1)          # 一个已配置信标, 不足以判室内
    sm.update("A", 2 * S, True, 10.0, 0)
    sm.update("A", 5 * S, True, 10.0, 0)
    assert sm.update("A", 8 * S, True, 10.0, 0) is None
    # 距最后一次有效 BLE 满 15 s 之后才允许转室外.
    assert sm.update("A", 16 * S, True, 10.0, 0) == io.MODE_OUTDOOR


def test_two_samples_with_two_beacons_go_indoor():
    sm = io.state_machine
    assert sm.update("A", 0, False, None, 2) is None
    assert sm.update("A", 5 * S, False, None, 3) == io.MODE_INDOOR


def test_single_beacon_samples_never_reach_indoor():
    sm = io.state_machine
    for t in (0, 3 * S, 6 * S, 9 * S):
        assert sm.update("A", t, False, None, 1) is None


def test_doorway_loitering_does_not_flap():
    """门口来回: 室外定下来之后, 零星单信标与稀疏 fix 都不该翻转状态."""
    sm = io.state_machine
    sm.update("A", 0, True, 10.0, 0)
    sm.update("A", 5 * S, True, 10.0, 0)
    assert sm.update("A", 10 * S, True, 10.0, 0) == io.MODE_OUTDOOR

    # 门口: 时而扫到 1 个信标, 时而没有; 条件都不成立 -> 保持室外.
    flips = 0
    mode = io.MODE_OUTDOOR
    for i, beacons in enumerate([1, 0, 1, 0, 1, 1, 0, 1]):
        t = (20 + i * 6) * S
        new_mode = sm.update("A", t, beacons == 0, 10.0, beacons)
        if new_mode != mode:
            flips += 1
            mode = new_mode
    assert flips == 0
    assert sm.get_mode("A") == io.MODE_OUTDOOR


def test_walking_indoors_switches_once():
    sm = io.state_machine
    sm.update("A", 0, True, 10.0, 0)
    sm.update("A", 5 * S, True, 10.0, 0)
    assert sm.update("A", 10 * S, True, 10.0, 0) == io.MODE_OUTDOOR
    # 真的走进室内: 连续两次都有 >= 2 个已配置信标.
    assert sm.update("A", 20 * S, False, None, 3) == io.MODE_OUTDOOR
    assert sm.update("A", 25 * S, False, None, 3) == io.MODE_INDOOR


def test_devices_are_isolated():
    sm = io.state_machine
    sm.update("A", 0, False, None, 2)
    sm.update("A", 5 * S, False, None, 2)
    assert sm.get_mode("A") == io.MODE_INDOOR
    assert sm.get_mode("B") is None


def test_configure_overrides_defaults():
    io.configure(outdoor_fix_count=1)
    sm = io.state_machine
    assert sm.update("A", 0, True, 10.0, 0) == io.MODE_OUTDOOR
    with pytest.raises(KeyError):
        io.configure(nonexistent_param=1)
