"""CPSA syntax generation and permissive validation."""
from __future__ import annotations
from collections import defaultdict
from .model import CPSAGraphicalProject, ParticipantDraft, ProtocolDraft


def sexpr(head: str, *items: str) -> str:
    """Create a simple one-line S-expression."""
    parts = [item for item in items if item]
    return f"({head}{(' ' + ' '.join(parts)) if parts else ''})"


def generate_cpsa(project: CPSAGraphicalProject) -> str:
    """Generate CPSA syntax for a project."""
    return "\n\n".join(generate_protocol(project, protocol) for protocol in project.semantic_model.protocols)


def generate_protocol(project: CPSAGraphicalProject, protocol: ProtocolDraft) -> str:
    """Generate CPSA defprotocol syntax."""
    model = project.semantic_model
    diagram = project.active_diagram()
    view_map = diagram.message_views_by_exchange_id() if diagram else {}
    events: dict[str, list[tuple[float, str]]] = defaultdict(list)
    exchange_map = model.exchanges_by_id()
    for exchange_id in protocol.message_exchange_ids:
        exchange = exchange_map.get(exchange_id)
        if not exchange:
            continue
        row = view_map[exchange.id].row_y() if exchange.id in view_map else exchange.ordinal_hint
        message = model.term_to_cpsa(exchange.message_term_id)
        if exchange.source_participant_id:
            events[exchange.source_participant_id].append((row, sexpr("send", message)))
        if exchange.target_participant_id:
            events[exchange.target_participant_id].append((row, sexpr("recv", message)))
    participants = model.participants_by_id()
    role_texts = []
    for participant_id in protocol.participant_ids:
        participant = participants.get(participant_id)
        if participant:
            role_texts.append(_generate_role(participant, events[participant_id]))
    body = "\n".join("  " + role for role in role_texts)
    return f"(defprotocol {protocol.name} {protocol.algebra}\n{body}\n)" if role_texts else f"(defprotocol {protocol.name} {protocol.algebra})"


def _generate_role(participant: ParticipantDraft, positioned_events: list[tuple[float, str]]) -> str:
    """Generate CPSA defrole syntax for one participant."""
    trace_events = [event for _, event in sorted(positioned_events, key=lambda positioned_event: positioned_event[0])]
    return sexpr("defrole", participant.role_symbol(), sexpr("trace", *trace_events))


def validate_project(project: CPSAGraphicalProject) -> list[str]:
    """Return permissive validation diagnostics."""
    messages: list[str] = []
    participant_ids = set(project.semantic_model.participants_by_id())
    term_ids = set(project.semantic_model.terms_by_id())
    for exchange in project.semantic_model.exchanges:
        if exchange.source_participant_id not in participant_ids:
            messages.append("Message has no valid source participant.")
        if exchange.target_participant_id not in participant_ids:
            messages.append("Message has no valid target participant.")
        if exchange.message_term_id not in term_ids:
            messages.append("Message has no valid term.")
    return messages
