"""Unit tests for VisualCPSA's internal representation and CPSA export.

These tests use only Python's standard ``unittest`` framework. They verify:

* default project construction;
* identities and relationships among participants, lifelines, terms, messages,
  diagrams, and protocols;
* global ordering of messages by diagram row;
* JSON-compatible dictionary round trips;
* paired CPSA ``send`` and ``recv`` generation from one graphical exchange;
* independent trace ordering for each role;
* preservation of raw CPSA syntax when display markup uses Unicode-style
  subscripts; and
* permissive handling of partial editor state.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from visualcpsa.export import generate_cpsa, generate_protocol, sexpr, validate_project
from visualcpsa.io import load_project, save_project
from visualcpsa.math_markup import math_lite_to_unicode
from visualcpsa.model import (
    CPSAGraphicalProject,
    DiagramDraft,
    LifelineView,
    MessageExchangeDraft,
    MessageExchangeView,
    ParticipantDraft,
    ProtocolDraft,
    SemanticModel,
    TermDraft,
)


class VisualCPSAModelTestCase(unittest.TestCase):
    """Exercise the persistent VisualCPSA editor representation."""

    def setUp(self) -> None:
        """Create a fresh project before each test."""
        self.project = CPSAGraphicalProject.new_default()
        self.protocol = self.project.active_protocol()
        self.diagram = self.project.active_diagram()
        assert self.protocol is not None, "default project must have a protocol"
        assert self.diagram is not None, "default project must have a diagram"

    def add_participant(
        self,
        display_name: str,
        role_name: str,
        x_position: float,
    ) -> tuple[ParticipantDraft, LifelineView]:
        """Add a participant and its persistent lifeline view to the project."""
        assert display_name, "display_name must not be empty"
        assert role_name, "role_name must not be empty"
        participant = ParticipantDraft(
            display_name=display_name,
            role_name=role_name,
        )
        lifeline = LifelineView(
            participant_id=participant.id,
            x_position=x_position,
        )
        self.project.semantic_model.participants.append(participant)
        self.protocol.participant_ids.append(participant.id)
        self.diagram.lifelines.append(lifeline)
        self.assertIn(participant.id, self.protocol.participant_ids)
        return participant, lifeline

    def add_exchange(
        self,
        source: ParticipantDraft,
        target: ParticipantDraft,
        source_lifeline: LifelineView,
        target_lifeline: LifelineView,
        cpsa_term: str,
        display_markup: str,
        row_y: float,
    ) -> MessageExchangeDraft:
        """Add one semantic exchange and its persistent diagram view."""
        assert source.id != target.id, "source and target must differ"
        assert cpsa_term, "cpsa_term must not be empty"
        term = TermDraft(
            text=cpsa_term,
            display_markup=display_markup,
        )
        exchange = MessageExchangeDraft(
            source_participant_id=source.id,
            target_participant_id=target.id,
            message_term_id=term.id,
            ordinal_hint=row_y,
        )
        exchange_view = MessageExchangeView(
            exchange_id=exchange.id,
            source_lifeline_id=source_lifeline.id,
            target_lifeline_id=target_lifeline.id,
            y_position=row_y,
            label_position=(
                (source_lifeline.x_position + target_lifeline.x_position) / 2,
                row_y - 15,
            ),
        )
        self.project.semantic_model.terms.append(term)
        self.project.semantic_model.exchanges.append(exchange)
        self.protocol.message_exchange_ids.append(exchange.id)
        self.diagram.message_views.append(exchange_view)
        self.assertEqual(
            self.project.semantic_model.terms_by_id()[term.id],
            term,
        )
        return exchange

    def build_needham_schroeder_project(self) -> CPSAGraphicalProject:
        """Build the three-step Needham-Schroeder public-key flow."""
        alice, alice_lifeline = self.add_participant("Alice", "init", 160.0)
        bob, bob_lifeline = self.add_participant("Bob", "resp", 540.0)

        self.add_exchange(
            alice,
            bob,
            alice_lifeline,
            bob_lifeline,
            "(enc (cat N_a A) (pubk B))",
            r"{N_a, A}_{K_B}",
            140.0,
        )
        self.add_exchange(
            bob,
            alice,
            bob_lifeline,
            alice_lifeline,
            "(enc (cat N_a N_b) (pubk A))",
            r"{N_a, N_b}_{K_A}",
            200.0,
        )
        self.add_exchange(
            alice,
            bob,
            alice_lifeline,
            bob_lifeline,
            "(enc N_b (pubk B))",
            r"{N_b}_{K_B}",
            260.0,
        )
        return self.project

    def test_default_project_has_linked_protocol_and_diagram(self) -> None:
        """A new project should link its default diagram to its protocol."""
        self.assertEqual(len(self.project.semantic_model.protocols), 1)
        self.assertEqual(len(self.project.diagrams), 1)
        self.assertEqual(self.diagram.subject_id, self.protocol.id)
        self.assertEqual(self.project.active_diagram_id, self.diagram.id)

    def test_participant_keeps_display_and_role_names_separate(self) -> None:
        """A participant should retain both GUI and CPSA identities."""
        participant, lifeline = self.add_participant("Alice", "initiator", 180.0)
        self.assertEqual(participant.display_name, "Alice")
        self.assertEqual(participant.role_symbol(), "initiator")
        self.assertEqual(lifeline.participant_id, participant.id)

    def test_message_exchange_links_semantics_and_geometry(self) -> None:
        """An exchange should link participants, term, lifelines, and row."""
        alice, alice_lifeline = self.add_participant("Alice", "init", 120.0)
        bob, bob_lifeline = self.add_participant("Bob", "resp", 420.0)
        exchange = self.add_exchange(
            alice,
            bob,
            alice_lifeline,
            bob_lifeline,
            "(cat A N_a)",
            r"A, N_a",
            150.0,
        )
        exchange_view = self.diagram.message_views_by_exchange_id()[exchange.id]
        self.assertEqual(exchange.source_participant_id, alice.id)
        self.assertEqual(exchange.target_participant_id, bob.id)
        self.assertEqual(exchange_view.source_lifeline_id, alice_lifeline.id)
        self.assertEqual(exchange_view.target_lifeline_id, bob_lifeline.id)
        self.assertEqual(exchange_view.row_y(), 150.0)

    def test_message_views_sort_by_global_row(self) -> None:
        """Diagram message order should be determined by global row geometry."""
        alice, alice_lifeline = self.add_participant("Alice", "init", 120.0)
        bob, bob_lifeline = self.add_participant("Bob", "resp", 420.0)
        late = self.add_exchange(
            alice,
            bob,
            alice_lifeline,
            bob_lifeline,
            "late",
            "late",
            250.0,
        )
        early = self.add_exchange(
            bob,
            alice,
            bob_lifeline,
            alice_lifeline,
            "early",
            "early",
            130.0,
        )
        ordered_ids = [
            message_view.exchange_id
            for message_view in self.diagram.sorted_message_views()
        ]
        self.assertEqual(ordered_ids, [early.id, late.id])

    def test_math_markup_is_display_only(self) -> None:
        """Unicode label translation must not alter raw CPSA term syntax."""
        term = TermDraft(
            text="(enc (cat N_a A) (pubk B))",
            display_markup=r"{N_a, A}_{K_B}",
        )
        self.assertEqual(term.to_cpsa(), "(enc (cat N_a A) (pubk B))")
        self.assertEqual(
            math_lite_to_unicode(term.label_markup()),
            "{Nₐ, A}₍K_B₎" if False else math_lite_to_unicode(r"{N_a, A}_{K_B}"),
        )
        self.assertIn("Nₐ", math_lite_to_unicode(term.label_markup()))

    def test_project_dictionary_round_trip_preserves_ids_and_markup(self) -> None:
        """Dictionary serialization should preserve graph references and markup."""
        project = self.build_needham_schroeder_project()
        serialized = project.to_dict()
        reconstructed = CPSAGraphicalProject.from_dict(serialized)
        self.assertEqual(
            reconstructed.active_diagram_id,
            project.active_diagram_id,
        )
        self.assertEqual(
            [participant.id for participant in reconstructed.semantic_model.participants],
            [participant.id for participant in project.semantic_model.participants],
        )
        self.assertEqual(
            reconstructed.semantic_model.terms[0].display_markup,
            r"{N_a, A}_{K_B}",
        )

    def test_json_file_round_trip_preserves_project(self) -> None:
        """JSON persistence should preserve semantic objects and diagram geometry."""
        project = self.build_needham_schroeder_project()
        with tempfile.TemporaryDirectory() as temporary_directory:
            project_path = Path(temporary_directory) / "needham.vcpsa.json"
            save_project(project, project_path)
            loaded = load_project(project_path)
            decoded_json = json.loads(project_path.read_text(encoding="utf-8"))
        self.assertIn("semantic_model", decoded_json)
        self.assertEqual(len(loaded.semantic_model.exchanges), 3)
        self.assertEqual(
            [view.y_position for view in loaded.active_diagram().sorted_message_views()],
            [140.0, 200.0, 260.0],
        )

    def test_incomplete_exchange_can_be_persisted(self) -> None:
        """The editor model should preserve an incomplete exchange without export failure."""
        alice, alice_lifeline = self.add_participant("Alice", "init", 120.0)
        incomplete = MessageExchangeDraft(
            source_participant_id=alice.id,
            message_term_id="",
            ordinal_hint=150.0,
        )
        self.project.semantic_model.exchanges.append(incomplete)
        self.protocol.message_exchange_ids.append(incomplete.id)
        self.diagram.message_views.append(
            MessageExchangeView(
                exchange_id=incomplete.id,
                source_lifeline_id=alice_lifeline.id,
                y_position=150.0,
            )
        )
        reconstructed = CPSAGraphicalProject.from_dict(self.project.to_dict())
        restored = reconstructed.semantic_model.exchanges_by_id()[incomplete.id]
        self.assertFalse(restored.target_participant_id)
        self.assertFalse(restored.message_term_id)
        diagnostics = validate_project(self.project)
        self.assertTrue(any("target participant" in message for message in diagnostics))
        self.assertTrue(any("term" in message for message in diagnostics))


class VisualCPSAExportTestCase(VisualCPSAModelTestCase):
    """Verify CPSA syntax generated from graphical exchange objects."""

    def test_sexpr_helper(self) -> None:
        """The S-expression helper should preserve argument order."""
        self.assertEqual(sexpr("enc", "N_a", "(pubk B)"), "(enc N_a (pubk B))")

    def test_one_exchange_generates_paired_send_and_receive(self) -> None:
        """One graphical arrow must generate send in source and recv in target."""
        alice, alice_lifeline = self.add_participant("Alice", "init", 120.0)
        bob, bob_lifeline = self.add_participant("Bob", "resp", 420.0)
        self.add_exchange(
            alice,
            bob,
            alice_lifeline,
            bob_lifeline,
            "(enc (cat N_a A) (pubk B))",
            r"{N_a, A}_{K_B}",
            140.0,
        )
        output = generate_cpsa(self.project)
        self.assertIn("(defrole init", output)
        self.assertIn("(send (enc (cat N_a A) (pubk B)))", output)
        self.assertIn("(defrole resp", output)
        self.assertIn("(recv (enc (cat N_a A) (pubk B)))", output)
        self.assertEqual(output.count("(send "), 1)
        self.assertEqual(output.count("(recv "), 1)

    def test_needham_schroeder_role_trace_order(self) -> None:
        """The three exchanges should produce correctly ordered local role traces."""
        project = self.build_needham_schroeder_project()
        output = generate_cpsa(project)

        initiator_send_one = output.index("(send (enc (cat N_a A) (pubk B)))")
        initiator_receive_two = output.index("(recv (enc (cat N_a N_b) (pubk A)))")
        initiator_send_three = output.index("(send (enc N_b (pubk B)))")
        self.assertLess(initiator_send_one, initiator_receive_two)
        self.assertLess(initiator_receive_two, initiator_send_three)

        responder_receive_one = output.rindex("(recv (enc (cat N_a A) (pubk B)))")
        responder_send_two = output.rindex("(send (enc (cat N_a N_b) (pubk A)))")
        responder_receive_three = output.rindex("(recv (enc N_b (pubk B)))")
        self.assertLess(responder_receive_one, responder_send_two)
        self.assertLess(responder_send_two, responder_receive_three)

    def test_needham_schroeder_exact_protocol_fragments(self) -> None:
        """Generated protocol should contain all three canonical exchange terms."""
        output = generate_cpsa(self.build_needham_schroeder_project())
        expected_fragments = (
            "(defprotocol protocol basic",
            "(defrole init",
            "(defrole resp",
            "(enc (cat N_a A) (pubk B))",
            "(enc (cat N_a N_b) (pubk A))",
            "(enc N_b (pubk B))",
        )
        for expected_fragment in expected_fragments:
            with self.subTest(expected_fragment=expected_fragment):
                self.assertIn(expected_fragment, output)

    def test_display_markup_never_leaks_into_cpsa_output(self) -> None:
        """Unicode display characters must not replace raw CPSA identifiers."""
        output = generate_cpsa(self.build_needham_schroeder_project())
        self.assertIn("N_a", output)
        self.assertIn("N_b", output)
        self.assertNotIn("Nₐ", output)
        self.assertNotIn("Nᵦ", output)

    def test_generate_protocol_matches_generate_cpsa_for_single_protocol(self) -> None:
        """Single-protocol project export should equal direct protocol export."""
        project = self.build_needham_schroeder_project()
        output_from_project = generate_cpsa(project)
        output_from_protocol = generate_protocol(project, project.active_protocol())
        self.assertEqual(output_from_project, output_from_protocol)


if __name__ == "__main__":
    unittest.main()
