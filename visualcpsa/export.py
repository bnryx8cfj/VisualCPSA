"""Strict CPSA syntax generation and permissive project diagnostics."""
from __future__ import annotations

from collections import defaultdict

from visualcpsa.exceptions import CPSAExportError, VisualCPSAError
from visualcpsa.logging_config import traced
from visualcpsa.model import CPSAGraphicalProject, ParticipantDraft, ProtocolDraft


@traced
def sexpr(head: str, *items: str) -> str:
    """Create a simple one-line S-expression with validated components."""
    if not isinstance(head, str) or not head.strip() or not all(isinstance(item, str) for item in items):
        raise CPSAExportError("S-expression head and items must be non-empty strings.")
    parts = [item for item in items if item]
    result = f"({head.strip()}{(' ' + ' '.join(parts)) if parts else ''})"
    assert result.startswith("(") and result.endswith(")"), "S-expression postcondition failed"
    return result


@traced
def generate_cpsa(project: CPSAGraphicalProject) -> str:
    """Generate strict CPSA syntax or raise CPSAExportError for incomplete state."""
    if not isinstance(project, CPSAGraphicalProject):
        raise CPSAExportError("generate_cpsa requires a CPSAGraphicalProject.")
    if not project.semantic_model.protocols:
        raise CPSAExportError("Project contains no protocol.")
    try:
        result = "\n\n".join(generate_protocol(project, protocol) for protocol in project.semantic_model.protocols)
    except VisualCPSAError as error:
        raise CPSAExportError(f"CPSA generation failed: {error}") from error
    if not result:
        raise CPSAExportError("CPSA generation produced no output.")
    assert "(defprotocol" in result, "CPSA output postcondition failed"
    return result


@traced
def generate_protocol(project: CPSAGraphicalProject, protocol: ProtocolDraft) -> str:
    """Generate one strict CPSA defprotocol expression."""
    if not isinstance(project, CPSAGraphicalProject) or not isinstance(protocol, ProtocolDraft):
        raise CPSAExportError("generate_protocol received invalid arguments.")
    model = project.semantic_model
    diagram = project.active_diagram()
    if diagram.require_subject_id() != protocol.id:
        raise CPSAExportError(f"Active diagram {diagram.id} does not describe protocol {protocol.id}.")
    view_map = diagram.message_views_by_exchange_id()
    events: dict[str, list[tuple[float, str]]] = defaultdict(list)
    for exchange_id in protocol.message_exchange_ids:
        exchange = model.require_exchange(exchange_id)
        source_id = exchange.require_source_participant_id()
        target_id = exchange.require_target_participant_id()
        model.require_participant(source_id)
        model.require_participant(target_id)
        message = model.require_term(exchange.require_message_term_id()).to_cpsa()
        message_view = view_map.get(exchange.id)
        row = message_view.row_y() if message_view else exchange.ordinal_hint
        events[source_id].append((row, sexpr("send", message)))
        events[target_id].append((row, sexpr("recv", message)))
    role_texts = [_generate_role(model.require_participant(participant_id), events[participant_id])
                  for participant_id in protocol.participant_ids]
    if not role_texts:
        raise CPSAExportError(f"Protocol {protocol.id} contains no participants.")
    body = "\n".join("  " + role for role in role_texts)
    result = f"(defprotocol {protocol.require_name()} {protocol.algebra}\n{body}\n)"
    assert result.startswith("(defprotocol"), "protocol export postcondition failed"
    return result


@traced
def _generate_role(participant: ParticipantDraft, positioned_events: list[tuple[float, str]]) -> str:
    """Generate one CPSA role with events sorted by their global diagram row."""
    if not isinstance(participant, ParticipantDraft):
        raise CPSAExportError("Role generation requires a ParticipantDraft.")
    trace_events = [event for row_position, event in sorted(positioned_events, key=lambda positioned_event: positioned_event[0])]
    result = sexpr("defrole", participant.role_symbol(), sexpr("trace", *trace_events))
    assert result.startswith("(defrole"), "role export postcondition failed"
    return result


@traced
def validate_project(project: CPSAGraphicalProject) -> list[str]:
    """Return permissive diagnostics without raising for incomplete draft references."""
    if not isinstance(project, CPSAGraphicalProject):
        raise TypeError("validate_project requires a CPSAGraphicalProject.")
    messages: list[str] = []
    participant_ids = set(project.semantic_model.participants_by_id())
    term_ids = set(project.semantic_model.terms_by_id())
    for exchange in project.semantic_model.exchanges:
        if exchange.source_participant_id not in participant_ids:
            messages.append(f"Exchange {exchange.id} has no valid source participant.")
        if exchange.target_participant_id not in participant_ids:
            messages.append(f"Exchange {exchange.id} has no valid target participant.")
        if exchange.message_term_id not in term_ids:
            messages.append(f"Exchange {exchange.id} has no valid term.")
    assert isinstance(messages, list), "diagnostic postcondition failed"
    return messages
