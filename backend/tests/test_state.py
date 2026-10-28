"""Tests for RunStateManager transitions."""

from app.core.state import RunStateManager, RunState


def test_state_machine_lifecycle():
    """Test transitions from IDLE -> VALIDATING -> RUNNING -> PAUSE_REQUESTED -> PAUSED -> RUNNING -> COMPLETED."""
    mgr = RunStateManager()
    assert mgr.state == RunState.IDLE

    # Start run
    assert mgr.start_run(run_id=1) is True
    assert mgr.state == RunState.VALIDATING
    assert mgr.active_run_id == 1

    # Cannot start another run while running
    assert mgr.start_run(run_id=2) is False

    # Transition to running
    mgr.set_running()
    assert mgr.state == RunState.RUNNING

    # Request pause
    assert mgr.request_pause() is True
    assert mgr.state == RunState.PAUSE_REQUESTED

    # Confirm pause
    mgr.confirm_pause()
    assert mgr.state == RunState.PAUSED

    # Resume
    assert mgr.resume() is True
    assert mgr.state == RunState.RUNNING

    # Stop request
    assert mgr.request_stop() is True
    assert mgr.state == RunState.STOP_REQUESTED

    # Confirm stop
    mgr.confirm_stop()
    assert mgr.state == RunState.STOPPED
    assert mgr.active_run_id is None
