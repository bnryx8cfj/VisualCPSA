"""Persistent project data model for VisualCPSA."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any
import itertools

_COUNTER = itertools.count(1)

def new_id(prefix: str) -> str:
    """Create a stable project-local identifier."""
    assert prefix, "prefix must not be empty"
    return f"{prefix}_{next(_COUNTER)}"

@dataclass
class TermDraft:
    """Draft message term with CPSA syntax and optional display markup."""
    id: str = field(default_factory=lambda: new_id("term"))
    text: str = "mesg"
    display_markup: str | None = None
    def label_markup(self) -> str:
        """Return display markup, falling back to CPSA text."""
        return self.display_markup if self.display_markup is not None else self.text
    def to_cpsa(self) -> str:
        """Return CPSA term syntax."""
        return self.text.strip() or "mesg"
    def to_dict(self) -> dict[str, Any]:
        """Serialize term."""
        return asdict(self)
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TermDraft":
        """Deserialize term."""
        return cls(**data)

@dataclass
class ParticipantDraft:
    """Participant lifeline with display name and CPSA role name."""
    id: str = field(default_factory=lambda: new_id("part"))
    display_name: str = "Participant"
    role_name: str = "role"
    def role_symbol(self) -> str:
        """Return CPSA role symbol."""
        return self.role_name or self.display_name or self.id
    def to_dict(self) -> dict[str, Any]:
        """Serialize participant."""
        return asdict(self)
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ParticipantDraft":
        """Deserialize participant."""
        return cls(**data)

@dataclass
class MessageExchangeDraft:
    """Editor message arrow that exports as paired send and receive events."""
    id: str = field(default_factory=lambda: new_id("msg"))
    source_participant_id: str | None = None
    target_participant_id: str | None = None
    message_term_id: str | None = None
    ordinal_hint: float = 0.0
    def to_dict(self) -> dict[str, Any]:
        """Serialize exchange."""
        return asdict(self)
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MessageExchangeDraft":
        """Deserialize exchange."""
        return cls(**data)

@dataclass
class ProtocolDraft:
    """Draft protocol grouping participants and message exchanges."""
    id: str = field(default_factory=lambda: new_id("proto"))
    name: str = "protocol"
    algebra: str = "basic"
    participant_ids: list[str] = field(default_factory=list)
    message_exchange_ids: list[str] = field(default_factory=list)
    def to_dict(self) -> dict[str, Any]:
        """Serialize protocol."""
        return asdict(self)
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProtocolDraft":
        """Deserialize protocol."""
        return cls(**data)

@dataclass
class DiagramStyle:
    """User-adjustable diagram spacing settings."""
    message_spacing: float = 60.0
    participant_top_margin: float = 70.0
    default_participant_spacing: float = 220.0
    endpoint_radius_ratio: float = 0.16
    min_endpoint_radius: float = 5.0
    max_endpoint_radius: float = 10.0
    def endpoint_radius(self) -> float:
        """Compute endpoint circle radius from message spacing."""
        assert self.message_spacing > 0, "message spacing must be positive"
        return max(self.min_endpoint_radius, min(self.max_endpoint_radius, self.message_spacing * self.endpoint_radius_ratio))
    def to_dict(self) -> dict[str, Any]:
        """Serialize style."""
        return asdict(self)
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DiagramStyle":
        """Deserialize style."""
        return cls(**data)

@dataclass
class LifelineView:
    """Persistent geometry for a participant lifeline."""
    id: str = field(default_factory=lambda: new_id("life"))
    participant_id: str = ""
    x: float = 120.0
    y_top: float = 70.0
    y_bottom: float = 760.0
    def to_dict(self) -> dict[str, Any]:
        """Serialize lifeline."""
        return asdict(self)
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LifelineView":
        """Deserialize lifeline."""
        return cls(**data)

@dataclass
class MessageExchangeView:
    """Persistent geometry for a horizontal message arrow."""
    id: str = field(default_factory=lambda: new_id("msgview"))
    exchange_id: str = ""
    source_lifeline_id: str | None = None
    target_lifeline_id: str | None = None
    y: float = 130.0
    label_position: tuple[float, float] | None = None
    def row_y(self) -> float:
        """Return message row coordinate."""
        return self.y
    def to_dict(self) -> dict[str, Any]:
        """Serialize message view."""
        data = asdict(self)
        data["label_position"] = list(self.label_position) if self.label_position else None
        return data
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MessageExchangeView":
        """Deserialize message view."""
        copied = dict(data)
        if copied.get("label_position") is not None:
            copied["label_position"] = tuple(copied["label_position"])
        return cls(**copied)

@dataclass
class DiagramDraft:
    """Diagram tab with persistent view geometry."""
    id: str = field(default_factory=lambda: new_id("diag"))
    name: str = "Main"
    subject_id: str | None = None
    style: DiagramStyle = field(default_factory=DiagramStyle)
    lifelines: list[LifelineView] = field(default_factory=list)
    message_views: list[MessageExchangeView] = field(default_factory=list)
    def lifelines_by_id(self) -> dict[str, LifelineView]:
        """Return lifelines by identifier."""
        return {item.id: item for item in self.lifelines}
    def message_views_by_exchange_id(self) -> dict[str, MessageExchangeView]:
        """Return message views by exchange identifier."""
        return {item.exchange_id: item for item in self.message_views}
    def sorted_message_views(self) -> list[MessageExchangeView]:
        """Return message views sorted by row."""
        return sorted(self.message_views, key=lambda item: item.row_y())
    def to_dict(self) -> dict[str, Any]:
        """Serialize diagram."""
        return {"id": self.id, "name": self.name, "subject_id": self.subject_id, "style": self.style.to_dict(), "lifelines": [item.to_dict() for item in self.lifelines], "message_views": [item.to_dict() for item in self.message_views]}
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DiagramDraft":
        """Deserialize diagram."""
        return cls(id=data.get("id", new_id("diag")), name=data.get("name", "Main"), subject_id=data.get("subject_id"), style=DiagramStyle.from_dict(data.get("style", {})), lifelines=[LifelineView.from_dict(item) for item in data.get("lifelines", [])], message_views=[MessageExchangeView.from_dict(item) for item in data.get("message_views", [])])

@dataclass
class SemanticModel:
    """Root semantic draft model."""
    protocols: list[ProtocolDraft] = field(default_factory=list)
    participants: list[ParticipantDraft] = field(default_factory=list)
    exchanges: list[MessageExchangeDraft] = field(default_factory=list)
    terms: list[TermDraft] = field(default_factory=list)
    def participants_by_id(self) -> dict[str, ParticipantDraft]:
        """Return participants by identifier."""
        return {item.id: item for item in self.participants}
    def exchanges_by_id(self) -> dict[str, MessageExchangeDraft]:
        """Return exchanges by identifier."""
        return {item.id: item for item in self.exchanges}
    def terms_by_id(self) -> dict[str, TermDraft]:
        """Return terms by identifier."""
        return {item.id: item for item in self.terms}
    def term_to_cpsa(self, term_id: str | None) -> str:
        """Render term by identifier."""
        term = self.terms_by_id().get(term_id or "")
        return term.to_cpsa() if term else "mesg"
    def term_label_markup(self, term_id: str | None) -> str:
        """Return term label markup by identifier."""
        term = self.terms_by_id().get(term_id or "")
        return term.label_markup() if term else "mesg"
    def to_dict(self) -> dict[str, Any]:
        """Serialize semantic model."""
        return {"protocols": [item.to_dict() for item in self.protocols], "participants": [item.to_dict() for item in self.participants], "exchanges": [item.to_dict() for item in self.exchanges], "terms": [item.to_dict() for item in self.terms]}
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SemanticModel":
        """Deserialize semantic model."""
        return cls(protocols=[ProtocolDraft.from_dict(item) for item in data.get("protocols", [])], participants=[ParticipantDraft.from_dict(item) for item in data.get("participants", [])], exchanges=[MessageExchangeDraft.from_dict(item) for item in data.get("exchanges", [])], terms=[TermDraft.from_dict(item) for item in data.get("terms", [])])

@dataclass
class CPSAGraphicalProject:
    """Persistent root project object."""
    semantic_model: SemanticModel = field(default_factory=SemanticModel)
    diagrams: list[DiagramDraft] = field(default_factory=list)
    active_diagram_id: str | None = None
    dirty: bool = False
    @classmethod
    def new_default(cls) -> "CPSAGraphicalProject":
        """Create a default project."""
        project = cls()
        protocol = ProtocolDraft()
        project.semantic_model.protocols.append(protocol)
        diagram = DiagramDraft(subject_id=protocol.id)
        project.diagrams.append(diagram)
        project.active_diagram_id = diagram.id
        return project
    def active_diagram(self) -> DiagramDraft | None:
        """Return active diagram."""
        for diagram in self.diagrams:
            if diagram.id == self.active_diagram_id:
                return diagram
        return self.diagrams[0] if self.diagrams else None
    def active_protocol(self) -> ProtocolDraft | None:
        """Return active protocol."""
        diagram = self.active_diagram()
        for protocol in self.semantic_model.protocols:
            if diagram and protocol.id == diagram.subject_id:
                return protocol
        return self.semantic_model.protocols[0] if self.semantic_model.protocols else None
    def mark_dirty(self) -> None:
        """Mark project as dirty."""
        self.dirty = True
    def to_dict(self) -> dict[str, Any]:
        """Serialize project."""
        return {"semantic_model": self.semantic_model.to_dict(), "diagrams": [item.to_dict() for item in self.diagrams], "active_diagram_id": self.active_diagram_id, "dirty": self.dirty}
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CPSAGraphicalProject":
        """Deserialize project."""
        return cls(semantic_model=SemanticModel.from_dict(data.get("semantic_model", {})), diagrams=[DiagramDraft.from_dict(item) for item in data.get("diagrams", [])], active_diagram_id=data.get("active_diagram_id"), dirty=bool(data.get("dirty", False)))
