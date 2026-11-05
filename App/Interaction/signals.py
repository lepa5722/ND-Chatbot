"""Signal detection (ED definitions frozen in the spec):
S1 explicit DA request, S2 explicit SRS request, S3 dismissal (short AND
no elaboration), S4 risk level from scenario metadata (never inferred).
Classifier output schema: {signal_id, emitted, confidence, source_span};
emit only at confidence >= CUTOFF; every detection is logged.
"""
from dataclasses import dataclass, field

CUTOFF = 0.7          # ED: below this, nothing is emitted (fail-safe)
SHORT_TOKENS = 15     # ED: S3 short-reply threshold

REQUEST_DA_PATTERNS = ("just tell me", "what should i do", "tell me what",
                       "give me the answer", "decide for me", "you decide")
REQUEST_SRS_PATTERNS = ("help me think", "let me reflect", "ask me questions",
                        "i want to talk it through", "help me explore")
DISMISSAL_MARKERS = ("whatever", "i don't know", "not really", "skip", "moving on")


@dataclass
class Signal:
    signal_id: str
    emitted: bool
    confidence: float
    source_span: str
    value: str = ""


def _tokens(text: str) -> list[str]:
    return text.lower().replace(",", " ").replace(".", " ").split()


def detect_signals(user_turn: str, pending_srs_prompt: bool,
                   elaboration_delta: int, scenario_risk: str | None) -> list[Signal]:
    text = user_turn.lower()
    signals: list[Signal] = []

    # S1 / S2: explicit requests (pattern match treated as high confidence)
    matched = next((p for p in REQUEST_DA_PATTERNS if p in text), None)
    signals.append(Signal("S1_request_DA", matched is not None,
                          0.95 if matched else 0.0, user_turn[:80], matched or ""))
    matched = next((p for p in REQUEST_SRS_PATTERNS if p in text), None)
    signals.append(Signal("S2_request_SRS", matched is not None,
                          0.95 if matched else 0.0, user_turn[:80], matched or ""))

    # S3: dismissal = short AND no elaboration, only while an SRS prompt is pending
    if pending_srs_prompt:
        short = len(_tokens(user_turn)) < SHORT_TOKENS
        no_elab = elaboration_delta == 0
        marker = next((m for m in DISMISSAL_MARKERS if m in text), None)
        confidence = 0.9 if marker else (0.8 if (short and no_elab) else 0.0)
        signals.append(Signal("S3_dismissal", confidence >= CUTOFF,
                              confidence, user_turn[:80]))
    else:
        signals.append(Signal("S3_dismissal", False, 0.0, ""))

    # S4: risk from scenario metadata only
    if scenario_risk in ("high", "medium", "low"):
        signals.append(Signal("S4_risk", True, 1.0, scenario_risk, scenario_risk))
    else:
        signals.append(Signal("S4_risk", False, 0.0, "", "uncertain"))

    return signals


def emitted(signals: list[Signal]) -> list[Signal]:
    return [s for s in signals if s.emitted]
