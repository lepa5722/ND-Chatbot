from datetime import datetime, timezone
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field
from app.logging.event_logger import append_event


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class AdaptationDecision(BaseModel):
    """Every proposal carries a logged evidence basis; the signal vocabulary
    excludes demographic attributes by construction (gap G6)."""

    model_config = ConfigDict(extra="forbid")
    ts: str = Field(default_factory=utcnow)
    session_id: str = "default"
    scenario_id: Optional[str] = None
    signal_type: str
    signal_value: str
    proposed_change: str
    evidence_basis: list[str]
    user_decision: Optional[Literal["accepted", "refused", "deferred"]] = None
    outcome: Optional[str] = None


class AdaptationController:
    ALLOWED_SIGNALS = {
        "repeated_answer_requests", "reflection_engaged",
        "reflection_dismissed", "high_risk_scenario", "low_risk_scenario",
        # spec v1.0 rule names (ED mapping, provenance logged)
        "explicit_request_DA", "explicit_request_SRS",
        "dismissal_count_gte_2", "fixation_detected_and_active_is_DA",
        "shallow_reasoning_and_active_is_SRS", "insufficient_evidence",
    }

    def __init__(self, interaction_controller):
        self.ic = interaction_controller
        self.pending: AdaptationDecision | None = None
        self.pre_proposal_approach: str | None = None

    def propose(self, signal_type: str, signal_value: str,
                session_id: str = "default",
                scenario_id: str | None = None) -> AdaptationDecision:
        if signal_type not in self.ALLOWED_SIGNALS:
            raise ValueError(f"Signal not in allowed vocabulary: {signal_type}")
        target = "SRS" if self.ic.active == "DA" else "DA"
        decision = AdaptationDecision(
            signal_type=signal_type, signal_value=signal_value,
            proposed_change=f"{self.ic.active}->{target}",
            evidence_basis=[f"{signal_type}: {signal_value}"],
            session_id=session_id, scenario_id=scenario_id,
        )
        self.pending = decision
        self.pre_proposal_approach = self.ic.active
        append_event(decision.model_dump() | {"event": "adaptation_decision"})
        return decision

    def decide(self, user_decision: str, session_id: str = "default") -> dict:
        d = self.pending
        if d is None:
            raise ValueError("No pending adaptation proposal.")
        d.user_decision = user_decision  # accepted | refused | deferred
        if user_decision == "accepted":
            self.ic.set_approach(d.proposed_change.split("->")[1], "policy",
                                 session_id, d.scenario_id)
            d.outcome = "switched"
        elif user_decision == "refused":
            if self.ic.active != self.pre_proposal_approach:
                self.ic.set_approach(self.pre_proposal_approach, "policy",
                                     session_id, d.scenario_id)
            d.outcome = "reverted"
        else:
            d.outcome = "deferred"
        append_event(d.model_dump() | {"event": "adaptation_outcome"})
        self.pending = None
        return d.model_dump()


# ---------------------------------------------------------------------------
# Profile-driven proposal path (spec v1.0). LI: Reflecti-Mate profile math +
# explore/exploit (profile.py, mode_selector.py). ED: category semantics,
# thresholds, precedence, mapping to DA/SRS, re-proposal block.
# ---------------------------------------------------------------------------
import os
import yaml as _yaml
from app.config import (EPSILON, RANDOM_SEED, FIXATION_SHARE,
                        FIXATION_MIN_THOUGHTS, SHALLOW_BELOW)
from app.adaptation.profile import Profile
from app.adaptation.mode_selector import ModeSelector
from app.adaptation.signals import detect_signals


class ProfileDrivenController(AdaptationController):
    """Rows 1-10 of the implementation table: signals -> profile -> mode ->
    target -> proposal -> user consent. Separate from the manual propose()
    path above; never merged into one opaque function."""

    def __init__(self, interaction_controller, epsilon: float = EPSILON,
                 seed: int = RANDOM_SEED, policy_version: str | None = None):
        super().__init__(interaction_controller)
        self.profile = Profile()
        self.selector = ModeSelector(epsilon, seed)
        self.seed = seed
        self.epsilon = epsilon
        pv = policy_version
        if pv is None:
            with open(os.path.join(os.path.dirname(__file__),
                                   "../interaction/policies/adaptive_support.yaml"),
                      encoding="utf-8") as f:
                pv = _yaml.safe_load(f)["policy_version"]
        self.policy_version = pv
        self.suppressed: list[dict] = []
        self.blocked_changes: dict[str, str] = {}   # session-scoped re-proposal block

    def register_turn(self, user_turn: str, pending_srs_prompt: bool,
                      elaboration_delta: int, scenario_risk: str | None = None,
                      session_id: str = "default", scenario_id: str | None = None) -> dict:
        """One turn: detect signals -> update profile -> decide proposal.
        Returns a full decision record including suppressed rules."""
        sigs = detect_signals(user_turn, pending_srs_prompt, elaboration_delta,
                              scenario_risk)
        # LI: profile update per turn (explore/exploit side handled by caller
        # after the response; here we record the profile state used).
        before = self.profile.snapshot()
        # ED: precedence. Highest wins; others logged as suppressed.
        em = {s.signal_id: s for s in sigs if s.emitted}
        s1 = "S1_request_DA" in em
        s2 = "S2_request_SRS" in em
        s3 = "S3_dismissal" in em
        active = self.ic.active
        proposal, rule, basis = None, "defer_no_proposal", []

        def blocked(target):
            return self.blocked_changes.get(session_id) == f"{active}->{target}"

        if s1 and not blocked("DA"):
            proposal, rule, basis = "DA", "explicit_request_DA", ["S1_request_DA"]
        elif s2 and not blocked("SRS"):
            proposal, rule, basis = "SRS", "explicit_request_SRS", ["S2_request_SRS"]
        elif s3 and not blocked("DA"):
            # ED: dismissal count >= 2 handled by caller incrementing a counter;
            # a single emitted S3 marks the trigger here.
            proposal, rule, basis = "DA", "dismissal_count_gte_2", ["S3_dismissal"]
        else:
            # LI: profile-driven explore/exploit
            mode = self.selector.select_mode()
            target = self.selector.select_target(mode, self.profile)
            fixation = any(self.profile.is_fixated(k, FIXATION_SHARE, FIXATION_MIN_THOUGHTS)
                           for k in ("help_seeking", "constraint"))
            shallow = self.profile.is_shallow("reflection", SHALLOW_BELOW)
            if fixation and active == "DA" and not blocked("SRS"):
                proposal, rule = "SRS", "fixation_detected_and_active_is_DA"
                basis = [f"fixation profile={before['totals']}"]
            elif shallow and active == "SRS":
                rule = "shallow_reasoning_and_active_is_SRS"
                basis = ["shallow reflection category"]
            elif fixation or shallow:
                rule = "no_change_needed"
                basis = [f"mode={mode} target={target}"]
            else:
                rule = "insufficient_evidence"
                basis = [f"mode={mode} target={target}"]

        record = {
            "session_id": session_id, "scenario_id": scenario_id,
            "policy_version": self.policy_version, "seed": self.seed,
            "epsilon": self.epsilon,
            "profile_before": before, "profile_after": self.profile.snapshot(),
            "active": active, "proposal": proposal, "rule": rule,
            "evidence_basis": basis,
            "signals": [s.__dict__ for s in sigs],
        }
        if proposal and proposal != active:
            decision = self.propose(
                signal_type=rule, signal_value="; ".join(basis),
                session_id=session_id, scenario_id=scenario_id)
            record["adaptation_decision_id"] = decision.ts
            self.blocked_changes[session_id] = f"{active}->{proposal}"
        record["suppressed"] = self.suppressed
        self.suppressed = []
        append_event(record | {"event": "adaptation_turn"})
        return record

