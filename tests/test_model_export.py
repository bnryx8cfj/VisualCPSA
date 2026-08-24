"""Tests for strict model resolvers, persistence, and CPSA generation."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from visualcpsa.exceptions import CPSAExportError, IncompleteModelError, PersistenceError
from visualcpsa.export import generate_cpsa, validate_project
from visualcpsa.io import load_project, save_project
from visualcpsa.math_markup import math_lite_to_unicode
from visualcpsa.model import CPSAGraphicalProject, LifelineView, MessageExchangeDraft, MessageExchangeView, ParticipantDraft, TermDraft


class ModelExportTests(unittest.TestCase):
    """Verify editor-state persistence and strict CPSA projection."""

    def build_project(self) -> CPSAGraphicalProject:
        """Create the three-message Needham-Schroeder graphical flow."""
        project = CPSAGraphicalProject.new_default()
        protocol, diagram = project.active_protocol(), project.active_diagram()
        alice, bob = ParticipantDraft(display_name="Alice", role_name="init"), ParticipantDraft(display_name="Bob", role_name="resp")
        project.semantic_model.participants.extend([alice, bob]); protocol.participant_ids.extend([alice.id, bob.id])
        alice_view, bob_view = LifelineView(participant_id=alice.id, x_position=160.0), LifelineView(participant_id=bob.id, x_position=540.0)
        diagram.lifelines.extend([alice_view, bob_view])
        messages = ((alice, bob, alice_view, bob_view, "(enc (cat N_a A) (pubk B))", r"{N_a, A}_{K_B}", 140.0),
                    (bob, alice, bob_view, alice_view, "(enc (cat N_a N_b) (pubk A))", r"{N_a, N_b}_{K_A}", 200.0),
                    (alice, bob, alice_view, bob_view, "(enc N_b (pubk B))", r"{N_b}_{K_B}", 260.0))
        for source, target, source_view, target_view, text, markup, row in messages:
            term = TermDraft(text=text, display_markup=markup)
            exchange = MessageExchangeDraft(source_participant_id=source.id, target_participant_id=target.id,
                                            message_term_id=term.id, ordinal_hint=row)
            project.semantic_model.terms.append(term); project.semantic_model.exchanges.append(exchange)
            protocol.message_exchange_ids.append(exchange.id)
            diagram.message_views.append(MessageExchangeView(exchange_id=exchange.id, source_lifeline_id=source_view.id,
                                                              target_lifeline_id=target_view.id, y_position=row,
                                                              label_position=((source_view.x_position + target_view.x_position) / 2, row - 15)))
        return project

    def test_strict_active_accessors_raise(self) -> None:
        """Operational accessors should raise rather than return optional values."""
        project = CPSAGraphicalProject()
        with self.assertRaises(IncompleteModelError):
            project.active_diagram()

    def test_incomplete_exchange_is_diagnosed_and_export_rejected(self) -> None:
        """Incomplete drafts remain representable but strict export rejects them."""
        project = CPSAGraphicalProject.new_default()
        protocol = project.active_protocol()
        exchange = MessageExchangeDraft()
        project.semantic_model.exchanges.append(exchange); protocol.message_exchange_ids.append(exchange.id)
        diagnostics = validate_project(project)
        self.assertEqual(len(diagnostics), 3)
        with self.assertRaises(CPSAExportError):
            generate_cpsa(project)

    def test_needham_schroeder_export_orders_role_traces(self) -> None:
        """The three graphical exchanges should produce ordered local role traces."""
        output = generate_cpsa(self.build_project())
        self.assertLess(output.index("(send (enc (cat N_a A) (pubk B)))"),
                        output.index("(recv (enc (cat N_a N_b) (pubk A)))"))
        self.assertIn("(send (enc N_b (pubk B)))", output)
        self.assertIn("(recv (enc N_b (pubk B)))", output)
        self.assertNotIn("Nₐ", output)

    def test_math_markup_handles_nonce_and_key_subscripts(self) -> None:
        """Display translation should handle Needham-Schroeder nonce and key labels."""
        rendered = math_lite_to_unicode(r"{N_a, N_b}_{K_B}")
        self.assertIn("Nₐ", rendered)
        self.assertIn("Nᵦ", rendered)
        self.assertIn("Kᵦ", rendered)

    def test_json_round_trip_preserves_geometry_and_markup(self) -> None:
        """JSON persistence should preserve rows, references, and display markup."""
        project = self.build_project()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "project.vcpsa.json"
            save_project(project, path)
            loaded = load_project(path)
        self.assertEqual([view.y_position for view in loaded.active_diagram().sorted_message_views()], [140.0, 200.0, 260.0])
        self.assertEqual(loaded.semantic_model.terms[0].display_markup, r"{N_a, A}_{K_B}")

    def test_malformed_project_json_raises_persistence_error(self) -> None:
        """Malformed project JSON should be wrapped in PersistenceError."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{bad", encoding="utf-8")
            with self.assertRaises(PersistenceError):
                load_project(path)


if __name__ == "__main__":
    unittest.main()
