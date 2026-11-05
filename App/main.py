from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

from app.models import ChatRequest, AdaptationProposalIn, AdaptationDecisionIn
from app.interaction.controller import InteractionController
from app.memory.manager import MemoryManager
from app.privacy.consent import ConsentState, check_consent, tag_sensitive, ConsentDenied
from app.adaptation.controller import AdaptationController
from app.llm.client import generate_response
from app.logging.event_logger import append_event

app = FastAPI(title="Privacy-Aware AI Companion",
              description="Research prototype for adaptive AI interaction approaches",
              version="0.1.0")

consent = ConsentState()
memory = MemoryManager()
controller = InteractionController()
adapter = AdaptationController(controller)


class ApproachIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approach: str
    selected_by: str = "user"          # "user" or "policy"
    session_id: str = "default"
    scenario_id: Optional[str] = None


class MemoryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str
    type: str = "user-relational"


class MemoryEditIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str


class ConsentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    granted: bool


@app.get("/health")
def health() -> dict:
    return {"status": "healthy", "approach": controller.active,
            "selected_by": controller.selected_by}


@app.post("/consent")
def set_consent(body: ConsentIn) -> dict:
    consent.granted = body.granted
    append_event({"event": "consent_change", "granted": body.granted,
                  "basis": consent.basis})
    return {"consent_granted": consent.granted}


@app.post("/approach")
def set_approach(body: ApproachIn) -> dict:
    try:
        event = controller.set_approach(body.approach, body.selected_by,
                                        body.session_id, body.scenario_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return event


@app.post("/chat")
def chat(body: ChatRequest) -> dict:
    try:
        check_consent(consent)
    except ConsentDenied as e:
        raise HTTPException(status_code=403, detail=str(e))
    tagged = tag_sensitive(body.message)
    prompt = controller.assemble_prompt(memory.permitted_context())
    reply = generate_response(prompt, tagged["content"])
    append_event({"event": "message_exchange", "session_id": body.session_id,
                  "scenario_id": body.scenario_id, "approach": controller.active,
                  "selected_by": controller.selected_by,
                  "sensitive_tags": tagged["sensitive_tags"]})
    return {"reply": reply, "approach": controller.active,
            "selected_by": controller.selected_by,
            "sensitive_tags": tagged["sensitive_tags"]}


@app.post("/memory")
def create_memory(body: MemoryIn) -> dict:
    entry = memory.create(body.content, body.type)
    return entry.model_dump()


@app.get("/memory")
def list_memory(include_deleted: bool = False) -> list[dict]:
    return [e.model_dump() for e in memory.read(include_deleted)]


@app.put("/memory/{entry_id}")
def edit_memory(entry_id: str, body: MemoryEditIn) -> dict:
    try:
        memory.edit(entry_id, body.content)
    except KeyError:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"edited": entry_id}


@app.delete("/memory/{entry_id}")
def delete_memory(entry_id: str) -> dict:
    try:
        memory.delete(entry_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"deleted": entry_id, "note": "entry excluded from all future reads"}


@app.post("/memory/reset")
def reset_memory() -> dict:
    return {"reset": memory.reset()}


@app.post("/adaptation/propose")
def propose_adaptation(body: AdaptationProposalIn) -> dict:
    try:
        d = adapter.propose(body.signal_type, body.signal_value,
                            body.session_id, body.scenario_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return d.model_dump()


@app.post("/adaptation/decision")
def decide_adaptation(body: AdaptationDecisionIn) -> dict:
    try:
        return adapter.decide(body.decision, body.session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
