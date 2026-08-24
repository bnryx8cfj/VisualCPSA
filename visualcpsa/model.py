"""Persistent, permissive editor model with strict operational resolvers for VisualCPSA."""
from __future__ import annotations

import itertools
import math
from dataclasses import asdict, dataclass, field
from typing import Any

from visualcpsa.exceptions import IncompleteModelError, ModelInvariantError, UnresolvedReferenceError
from visualcpsa.logging_config import traced

_COUNTER = itertools.count(1)


@traced
def new_id(prefix: str) -> str:
    """Create a stable project-local identifier."""
    if not isinstance(prefix, str) or not prefix.strip():
        raise ModelInvariantError("Identifier prefix must be a non-empty string.")
    identifier = f"{prefix.strip()}_{next(_COUNTER)}"
    assert identifier.startswith(prefix.strip() + "_"), "identifier prefix postcondition failed"
    return identifier


@dataclass
class TermDraft:
    """Draft message term with CPSA syntax and optional display behavior represented without Optional types."""

    id: str = field(default_factory=lambda: new_id("term"))
    text: str = "mesg"
    display_markup: str = ""

    def __post_init__(self) -> None:
        """Validate term invariants."""
        if not self.id or not isinstance(self.text, str) or not isinstance(self.display_markup, str):
            raise ModelInvariantError("Term fields have invalid values.")

    @traced
    def label_markup(self) -> str:
        """Return display markup, falling back to CPSA text."""
        label = self.display_markup or self.text
        assert isinstance(label, str), "term label must be text"
        return label

    @traced
    def to_cpsa(self) -> str:
        """Return strict CPSA term syntax or raise IncompleteModelError."""
        rendered = self.text.strip()
        if not rendered:
            raise IncompleteModelError(f"Term {self.id} has no CPSA syntax.")
        assert rendered, "term rendering postcondition failed"
        return rendered

    def to_dict(self) -> dict[str, Any]:
        """Serialize the term."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TermDraft":
        """Deserialize the term."""
        if not isinstance(data, dict):
            raise ModelInvariantError("Term data must be an object.")
        return cls(**data)


@dataclass
class ParticipantDraft:
    """Participant lifeline with separate GUI display and CPSA role names."""

    id: str = field(default_factory=lambda: new_id("part"))
    display_name: str = "Participant"
    role_name: str = "role"

    def __post_init__(self) -> None:
        """Validate participant invariants."""
        if not self.id or not isinstance(self.display_name, str) or not isinstance(self.role_name, str):
            raise ModelInvariantError("Participant fields have invalid values.")

    @traced
    def role_symbol(self) -> str:
        """Return a concrete CPSA role symbol or raise IncompleteModelError."""
        symbol = self.role_name.strip()
        if not symbol:
            raise IncompleteModelError(f"Participant {self.id} has no CPSA role name.")
        assert symbol, "role symbol postcondition failed"
        return symbol

    def to_dict(self) -> dict[str, Any]:
        """Serialize the participant."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ParticipantDraft":
        """Deserialize the participant."""
        if not isinstance(data, dict):
            raise ModelInvariantError("Participant data must be an object.")
        return cls(**data)


@dataclass
class MessageExchangeDraft:
    """Editor message arrow that exports as paired send and receive events."""

    id: str = field(default_factory=lambda: new_id("msg"))
    source_participant_id: str = ""
    target_participant_id: str = ""
    message_term_id: str = ""
    ordinal_hint: float = 0.0

    def __post_init__(self) -> None:
        """Validate serializable exchange field types while permitting empty draft references."""
        if not self.id or not all(isinstance(value, str) for value in
                                 (self.source_participant_id, self.target_participant_id, self.message_term_id)):
            raise ModelInvariantError("Message exchange fields have invalid values.")
        if not math.isfinite(self.ordinal_hint):
            raise ModelInvariantError("Message exchange ordinal must be finite.")

    def require_source_participant_id(self) -> str:
        """Return source participant id or raise IncompleteModelError."""
        if not self.source_participant_id:
            raise IncompleteModelError(f"Exchange {self.id} has no source participant.")
        return self.source_participant_id

    def require_target_participant_id(self) -> str:
        """Return target participant id or raise IncompleteModelError."""
        if not self.target_participant_id:
            raise IncompleteModelError(f"Exchange {self.id} has no target participant.")
        return self.target_participant_id

    def require_message_term_id(self) -> str:
        """Return message term id or raise IncompleteModelError."""
        if not self.message_term_id:
            raise IncompleteModelError(f"Exchange {self.id} has no message term.")
        return self.message_term_id

    def to_dict(self) -> dict[str, Any]:
        """Serialize the exchange."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MessageExchangeDraft":
        """Deserialize the exchange, migrating legacy null references to empty strings."""
        if not isinstance(data, dict):
            raise ModelInvariantError("Exchange data must be an object.")
        migrated = dict(data)
        for key in ("source_participant_id", "target_participant_id", "message_term_id"):
            migrated[key] = migrated.get(key) or ""
        return cls(**migrated)


@dataclass
class ProtocolDraft:
    """Draft protocol grouping participants and message exchanges."""

    id: str = field(default_factory=lambda: new_id("proto"))
    name: str = "protocol"
    algebra: str = "basic"
    participant_ids: list[str] = field(default_factory=list)
    message_exchange_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate protocol invariants."""
        if not self.id or self.algebra not in {"basic", "diffie-hellman"}:
            raise ModelInvariantError("Protocol id or algebra is invalid.")
        if len(set(self.participant_ids)) != len(self.participant_ids):
            raise ModelInvariantError("Protocol participant ids must be unique.")
        if len(set(self.message_exchange_ids)) != len(self.message_exchange_ids):
            raise ModelInvariantError("Protocol exchange ids must be unique.")

    def require_name(self) -> str:
        """Return protocol name or raise IncompleteModelError."""
        name = self.name.strip()
        if not name:
            raise IncompleteModelError(f"Protocol {self.id} has no name.")
        return name

    def to_dict(self) -> dict[str, Any]:
        """Serialize the protocol."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProtocolDraft":
        """Deserialize the protocol."""
        if not isinstance(data, dict):
            raise ModelInvariantError("Protocol data must be an object.")
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

    def __post_init__(self) -> None:
        """Validate style invariants."""
        values = (self.message_spacing, self.participant_top_margin, self.default_participant_spacing,
                  self.endpoint_radius_ratio, self.min_endpoint_radius, self.max_endpoint_radius)
        if not all(math.isfinite(value) for value in values) or self.message_spacing <= 0:
            raise ModelInvariantError("Diagram style values must be finite and spacing must be positive.")
        if self.min_endpoint_radius <= 0 or self.max_endpoint_radius < self.min_endpoint_radius:
            raise ModelInvariantError("Endpoint radius bounds are invalid.")

    @traced
    def endpoint_radius(self) -> float:
        """Compute endpoint circle radius from message spacing."""
        radius = max(self.min_endpoint_radius, min(self.max_endpoint_radius, self.message_spacing * self.endpoint_radius_ratio))
        assert self.min_endpoint_radius <= radius <= self.max_endpoint_radius, "radius postcondition failed"
        return radius

    def to_dict(self) -> dict[str, Any]:
        """Serialize the style."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DiagramStyle":
        """Deserialize the style."""
        if not isinstance(data, dict):
            raise ModelInvariantError("Diagram style data must be an object.")
        return cls(**data)


@dataclass
class LifelineView:
    """Persistent geometry for a participant lifeline."""

    id: str = field(default_factory=lambda: new_id("life"))
    participant_id: str = ""
    x_position: float = 120.0
    y_top: float = 70.0
    y_bottom: float = 760.0

    def __post_init__(self) -> None:
        """Validate lifeline geometry while permitting an empty draft participant reference."""
        if not self.id or not all(math.isfinite(value) for value in (self.x_position, self.y_top, self.y_bottom)):
            raise ModelInvariantError("Lifeline fields are invalid.")
        if self.y_bottom < self.y_top:
            raise ModelInvariantError("Lifeline bottom must not be above its top.")

    def require_participant_id(self) -> str:
        """Return participant id or raise IncompleteModelError."""
        if not self.participant_id:
            raise IncompleteModelError(f"Lifeline {self.id} has no participant.")
        return self.participant_id

    def to_dict(self) -> dict[str, Any]:
        """Serialize the lifeline."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LifelineView":
        """Deserialize the lifeline."""
        if not isinstance(data, dict):
            raise ModelInvariantError("Lifeline data must be an object.")
        migrated = dict(data)
        if "x_position" not in migrated and "x" in migrated:
            migrated["x_position"] = migrated.pop("x")
        return cls(**migrated)


@dataclass
class MessageExchangeView:
    """Persistent geometry for a horizontal message arrow."""

    id: str = field(default_factory=lambda: new_id("msgview"))
    exchange_id: str = ""
    source_lifeline_id: str = ""
    target_lifeline_id: str = ""
    y_position: float = 130.0
    label_position: tuple[float, float] = (0.0, 0.0)

    def __post_init__(self) -> None:
        """Validate view geometry while permitting empty draft references."""
        if not self.id or not math.isfinite(self.y_position) or len(self.label_position) != 2:
            raise ModelInvariantError("Message view fields are invalid.")
        if not all(math.isfinite(value) for value in self.label_position):
            raise ModelInvariantError("Message label position must be finite.")

    @traced
    def row_y(self) -> float:
        """Return message row coordinate."""
        assert math.isfinite(self.y_position), "message row invariant failed"
        return self.y_position

    def require_exchange_id(self) -> str:
        """Return exchange id or raise IncompleteModelError."""
        if not self.exchange_id:
            raise IncompleteModelError(f"Message view {self.id} has no exchange.")
        return self.exchange_id

    def require_source_lifeline_id(self) -> str:
        """Return source lifeline id or raise IncompleteModelError."""
        if not self.source_lifeline_id:
            raise IncompleteModelError(f"Message view {self.id} has no source lifeline.")
        return self.source_lifeline_id

    def require_target_lifeline_id(self) -> str:
        """Return target lifeline id or raise IncompleteModelError."""
        if not self.target_lifeline_id:
            raise IncompleteModelError(f"Message view {self.id} has no target lifeline.")
        return self.target_lifeline_id

    def to_dict(self) -> dict[str, Any]:
        """Serialize the message view."""
        data = asdict(self)
        data["label_position"] = list(self.label_position)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MessageExchangeView":
        """Deserialize the message view and migrate legacy null values."""
        if not isinstance(data, dict):
            raise ModelInvariantError("Message view data must be an object.")
        migrated = dict(data)
        if "y_position" not in migrated and "y" in migrated:
            migrated["y_position"] = migrated.pop("y")
        for key in ("exchange_id", "source_lifeline_id", "target_lifeline_id"):
            migrated[key] = migrated.get(key) or ""
        migrated["label_position"] = tuple(migrated.get("label_position") or (0.0, 0.0))
        return cls(**migrated)


@dataclass
class DiagramDraft:
    """Diagram tab containing persistent geometry."""

    id: str = field(default_factory=lambda: new_id("diag"))
    name: str = "Main"
    subject_id: str = ""
    style: DiagramStyle = field(default_factory=DiagramStyle)
    lifelines: list[LifelineView] = field(default_factory=list)
    message_views: list[MessageExchangeView] = field(default_factory=list)

    def require_subject_id(self) -> str:
        """Return subject protocol id or raise IncompleteModelError."""
        if not self.subject_id:
            raise IncompleteModelError(f"Diagram {self.id} has no subject protocol.")
        return self.subject_id

    def lifelines_by_id(self) -> dict[str, LifelineView]:
        """Return lifelines by identifier and reject duplicate ids."""
        mapping = {item.id: item for item in self.lifelines}
        if len(mapping) != len(self.lifelines):
            raise ModelInvariantError("Diagram contains duplicate lifeline ids.")
        return mapping

    def message_views_by_exchange_id(self) -> dict[str, MessageExchangeView]:
        """Return message views by exchange identifier and reject duplicates."""
        mapping = {item.exchange_id: item for item in self.message_views if item.exchange_id}
        if len(mapping) != len([item for item in self.message_views if item.exchange_id]):
            raise ModelInvariantError("Diagram contains duplicate exchange views.")
        return mapping

    def sorted_message_views(self) -> list[MessageExchangeView]:
        """Return message views sorted by row without changing the source collection."""
        result = sorted(self.message_views, key=lambda item: item.row_y())
        assert len(result) == len(self.message_views), "message sorting changed collection size"
        return result

    def to_dict(self) -> dict[str, Any]:
        """Serialize the diagram."""
        return {"id": self.id, "name": self.name, "subject_id": self.subject_id, "style": self.style.to_dict(),
                "lifelines": [item.to_dict() for item in self.lifelines],
                "message_views": [item.to_dict() for item in self.message_views]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DiagramDraft":
        """Deserialize the diagram and migrate a legacy null subject id."""
        if not isinstance(data, dict):
            raise ModelInvariantError("Diagram data must be an object.")
        return cls(id=data.get("id") or new_id("diag"), name=data.get("name", "Main"), subject_id=data.get("subject_id") or "",
                   style=DiagramStyle.from_dict(data.get("style", {})),
                   lifelines=[LifelineView.from_dict(item) for item in data.get("lifelines", [])],
                   message_views=[MessageExchangeView.from_dict(item) for item in data.get("message_views", [])])


@dataclass
class SemanticModel:
    """Root semantic draft model with strict identifier resolvers."""

    protocols: list[ProtocolDraft] = field(default_factory=list)
    participants: list[ParticipantDraft] = field(default_factory=list)
    exchanges: list[MessageExchangeDraft] = field(default_factory=list)
    terms: list[TermDraft] = field(default_factory=list)

    def _unique_map(self, items: list[Any], label: str) -> dict[str, Any]:
        """Return an id map and raise ModelInvariantError for duplicate ids."""
        mapping = {item.id: item for item in items}
        if len(mapping) != len(items):
            raise ModelInvariantError(f"Semantic model contains duplicate {label} ids.")
        return mapping

    def protocols_by_id(self) -> dict[str, ProtocolDraft]:
        """Return protocols by identifier."""
        return self._unique_map(self.protocols, "protocol")

    def participants_by_id(self) -> dict[str, ParticipantDraft]:
        """Return participants by identifier."""
        return self._unique_map(self.participants, "participant")

    def exchanges_by_id(self) -> dict[str, MessageExchangeDraft]:
        """Return exchanges by identifier."""
        return self._unique_map(self.exchanges, "exchange")

    def terms_by_id(self) -> dict[str, TermDraft]:
        """Return terms by identifier."""
        return self._unique_map(self.terms, "term")

    def require_participant(self, participant_id: str) -> ParticipantDraft:
        """Resolve a participant or raise UnresolvedReferenceError."""
        try:
            return self.participants_by_id()[participant_id]
        except KeyError as error:
            raise UnresolvedReferenceError(f"Unknown participant id: {participant_id}") from error

    def require_exchange(self, exchange_id: str) -> MessageExchangeDraft:
        """Resolve an exchange or raise UnresolvedReferenceError."""
        try:
            return self.exchanges_by_id()[exchange_id]
        except KeyError as error:
            raise UnresolvedReferenceError(f"Unknown exchange id: {exchange_id}") from error

    def require_term(self, term_id: str) -> TermDraft:
        """Resolve a term or raise UnresolvedReferenceError."""
        try:
            return self.terms_by_id()[term_id]
        except KeyError as error:
            raise UnresolvedReferenceError(f"Unknown term id: {term_id}") from error

    def term_preview_or_placeholder(self, term_id: str) -> str:
        """Return a safe GUI preview without making strict export permissive."""
        if not term_id:
            return "mesg"
        term = self.terms_by_id().get(term_id)
        return term.to_cpsa() if term else "mesg"

    def term_label_or_placeholder(self, term_id: str) -> str:
        """Return safe GUI label markup for an unresolved draft reference."""
        if not term_id:
            return "mesg"
        term = self.terms_by_id().get(term_id)
        return term.label_markup() if term else "mesg"

    def to_dict(self) -> dict[str, Any]:
        """Serialize the semantic model."""
        return {"protocols": [item.to_dict() for item in self.protocols],
                "participants": [item.to_dict() for item in self.participants],
                "exchanges": [item.to_dict() for item in self.exchanges], "terms": [item.to_dict() for item in self.terms]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SemanticModel":
        """Deserialize the semantic model."""
        if not isinstance(data, dict):
            raise ModelInvariantError("Semantic model data must be an object.")
        model = cls(protocols=[ProtocolDraft.from_dict(item) for item in data.get("protocols", [])],
                    participants=[ParticipantDraft.from_dict(item) for item in data.get("participants", [])],
                    exchanges=[MessageExchangeDraft.from_dict(item) for item in data.get("exchanges", [])],
                    terms=[TermDraft.from_dict(item) for item in data.get("terms", [])])
        model.protocols_by_id(); model.participants_by_id(); model.exchanges_by_id(); model.terms_by_id()
        return model


@dataclass
class CPSAGraphicalProject:
    """Persistent root project with strict active-object accessors."""

    semantic_model: SemanticModel = field(default_factory=SemanticModel)
    diagrams: list[DiagramDraft] = field(default_factory=list)
    active_diagram_id: str = ""
    dirty: bool = False

    @classmethod
    def new_default(cls) -> "CPSAGraphicalProject":
        """Create a default project with one linked protocol and diagram."""
        project = cls()
        protocol = ProtocolDraft()
        project.semantic_model.protocols.append(protocol)
        diagram = DiagramDraft(subject_id=protocol.id)
        project.diagrams.append(diagram)
        project.active_diagram_id = diagram.id
        assert project.active_protocol() is protocol, "default project linkage failed"
        return project

    def diagrams_by_id(self) -> dict[str, DiagramDraft]:
        """Return diagrams by identifier and reject duplicates."""
        mapping = {item.id: item for item in self.diagrams}
        if len(mapping) != len(self.diagrams):
            raise ModelInvariantError("Project contains duplicate diagram ids.")
        return mapping

    def active_diagram(self) -> DiagramDraft:
        """Return active diagram or raise IncompleteModelError/UnresolvedReferenceError."""
        if not self.active_diagram_id:
            raise IncompleteModelError("Project has no active diagram id.")
        try:
            return self.diagrams_by_id()[self.active_diagram_id]
        except KeyError as error:
            raise UnresolvedReferenceError(f"Unknown active diagram id: {self.active_diagram_id}") from error

    def active_protocol(self) -> ProtocolDraft:
        """Return active protocol or raise a specific model exception."""
        subject_id = self.active_diagram().require_subject_id()
        try:
            return self.semantic_model.protocols_by_id()[subject_id]
        except KeyError as error:
            raise UnresolvedReferenceError(f"Unknown protocol id for active diagram: {subject_id}") from error

    def mark_dirty(self) -> None:
        """Mark project dirty and verify the postcondition."""
        self.dirty = True
        assert self.dirty is True, "dirty-state postcondition failed"

    def to_dict(self) -> dict[str, Any]:
        """Serialize the project."""
        return {"semantic_model": self.semantic_model.to_dict(), "diagrams": [item.to_dict() for item in self.diagrams],
                "active_diagram_id": self.active_diagram_id, "dirty": self.dirty}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CPSAGraphicalProject":
        """Deserialize the project and migrate a legacy null active diagram id."""
        if not isinstance(data, dict):
            raise ModelInvariantError("Project data must be an object.", repr(data))
        project = cls(semantic_model=SemanticModel.from_dict(data.get("semantic_model", {})),
                      diagrams=[DiagramDraft.from_dict(item) for item in data.get("diagrams", [])],
                      active_diagram_id=data.get("active_diagram_id") or "", dirty=bool(data.get("dirty", False)))
        project.diagrams_by_id()
        return project
