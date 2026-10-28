"""Run state machine and active operation tracking."""

from enum import Enum
import threading
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class RunState(str, Enum):
    """Explicit lifecycle states for screening runs."""
    IDLE = "IDLE"
    VALIDATING = "VALIDATING"
    RUNNING = "RUNNING"
    PAUSE_REQUESTED = "PAUSE_REQUESTED"
    PAUSED = "PAUSED"
    STOP_REQUESTED = "STOP_REQUESTED"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class CurrentOperation(BaseModel):
    """Real-time operation detail for 'What is the agent doing right now?' panel."""
    current_operation: str = Field(default="Agent is idle", description="Human-readable description of current task")
    workflow_stage: str = Field(default="IDLE", description="Active workflow stage name")
    candidate_reference: Optional[str] = Field(default=None, description="Identifier of candidate being inspected")
    current_status: str = Field(default="Ready to start", description="Current execution status")
    last_completed_action: Optional[str] = Field(default=None, description="Last successfully executed step")
    next_planned_action: Optional[str] = Field(default=None, description="Upcoming operation")
    warning_or_error: Optional[str] = Field(default=None, description="Active warning or error message")


class RunStateManager:
    """Thread-safe state manager for the screening agent lifecycle."""

    def __init__(self):
        self._lock = threading.Lock()
        self._state: RunState = RunState.IDLE
        self._active_run_id: Optional[int] = None
        self._active_technology: str = "golang"
        self._current_op: CurrentOperation = CurrentOperation()

    @property
    def state(self) -> RunState:
        with self._lock:
            return self._state

    @property
    def active_run_id(self) -> Optional[int]:
        with self._lock:
            return self._active_run_id

    @property
    def active_technology(self) -> str:
        with self._lock:
            return self._active_technology

    @property
    def current_operation(self) -> CurrentOperation:
        with self._lock:
            return self._current_op.model_copy()

    def set_state(self, new_state: RunState) -> None:
        """Update run state."""
        with self._lock:
            self._state = new_state

    def start_run(self, run_id: int, technology: str = "golang") -> bool:
        """Transition from IDLE, COMPLETED, STOPPED, or FAILED to VALIDATING."""
        with self._lock:
            if self._state in (RunState.RUNNING, RunState.VALIDATING, RunState.PAUSE_REQUESTED):
                return False
            self._state = RunState.VALIDATING
            self._active_run_id = run_id
            self._active_technology = technology
            self._current_op = CurrentOperation(
                current_operation=f"Validating configuration and credentials for {technology.upper()}",
                workflow_stage="Configuration validation",
                current_status="Initializing run",
                next_planned_action=f"Verify search URL and browser session for {technology.upper()}",
            )
            return True

    def set_running(self) -> None:
        with self._lock:
            self._state = RunState.RUNNING

    def request_pause(self) -> bool:
        """Request a safe pause."""
        with self._lock:
            if self._state == RunState.RUNNING:
                self._state = RunState.PAUSE_REQUESTED
                self._current_op.current_status = "Pause requested. Finishing current atomic step."
                return True
            return False

    def confirm_pause(self) -> None:
        """Acknowledge and enter PAUSED state."""
        with self._lock:
            self._state = RunState.PAUSED
            self._current_op.current_status = "Paused at safe checkpoint."
            self._current_op.current_operation = "Screening is paused."

    def resume(self) -> bool:
        """Resume from PAUSED state."""
        with self._lock:
            if self._state == RunState.PAUSED:
                self._state = RunState.RUNNING
                self._current_op.current_status = "Resumed. Continuing from last checkpoint."
                return True
            return False

    def request_stop(self) -> bool:
        """Request a safe stop."""
        with self._lock:
            if self._state in (RunState.RUNNING, RunState.PAUSED, RunState.PAUSE_REQUESTED, RunState.VALIDATING):
                self._state = RunState.STOP_REQUESTED
                self._current_op.current_status = "Stop requested. Safely wrapping up operations."
                return True
            return False

    def confirm_stop(self) -> None:
        """Acknowledge and enter STOPPED state."""
        with self._lock:
            self._state = RunState.STOPPED
            self._active_run_id = None
            self._current_op = CurrentOperation(
                current_operation="Agent stopped",
                workflow_stage="STOPPED",
                current_status="Stopped safely by user",
                last_completed_action="All progress persisted to database",
            )

    def complete_run(self) -> None:
        """Mark run as completed."""
        with self._lock:
            self._state = RunState.COMPLETED
            self._active_run_id = None
            self._current_op = CurrentOperation(
                current_operation="Screening run complete",
                workflow_stage="Completion",
                current_status="All available candidates processed",
                last_completed_action="Run results saved",
            )

    def fail_run(self, error_message: str) -> None:
        """Mark run as failed with error."""
        with self._lock:
            self._state = RunState.FAILED
            self._active_run_id = None
            self._current_op.warning_or_error = error_message
            self._current_op.current_status = f"Failed: {error_message}"

    def update_operation(
        self,
        current_operation: Optional[str] = None,
        workflow_stage: Optional[str] = None,
        candidate_reference: Optional[str] = None,
        current_status: Optional[str] = None,
        last_completed_action: Optional[str] = None,
        next_planned_action: Optional[str] = None,
        warning_or_error: Optional[str] = None,
    ) -> None:
        """Update live operation details."""
        with self._lock:
            if current_operation is not None:
                self._current_op.current_operation = current_operation
            if workflow_stage is not None:
                self._current_op.workflow_stage = workflow_stage
            if candidate_reference is not None:
                self._current_op.candidate_reference = candidate_reference
            if current_status is not None:
                self._current_op.current_status = current_status
            if last_completed_action is not None:
                self._current_op.last_completed_action = last_completed_action
            if next_planned_action is not None:
                self._current_op.next_planned_action = next_planned_action
            if warning_or_error is not None:
                self._current_op.warning_or_error = warning_or_error


# Singleton instance
state_manager = RunStateManager()
