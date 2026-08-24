"""Unit tests for settings, argparse defaults, math-lite markup, and export."""
from __future__ import annotations
from pathlib import Path
import tempfile
import unittest
from main import build_argument_parser
from visualcpsa.export import generate_cpsa
from visualcpsa.math_markup import math_lite_to_unicode
from visualcpsa.model import CPSAGraphicalProject, LifelineView, MessageExchangeDraft, MessageExchangeView, ParticipantDraft, TermDraft
from visualcpsa.settings import Settings

class VisualCPSASplashTests(unittest.TestCase):
    """Test splash-related settings and core export behavior."""
    def test_settings_default_and_roundtrip(self) -> None:
        """Settings should default to show_intro true and round-trip to JSON."""
        with tempfile.TemporaryDirectory() as directory:
            settings_path = Path(directory) / "settings.json"
            settings = Settings.load(settings_path)
            self.assertTrue(settings.show_intro)
            settings.show_intro = False
            settings.save(settings_path)
            self.assertFalse(Settings.load(settings_path).show_intro)
    def test_argparse_default_config(self) -> None:
        """Argument parser should expose a default config path."""
        parser = build_argument_parser(settings=Settings())
        arguments = parser.parse_args([])
        self.assertTrue(str(arguments.config).endswith("visualcpsa_settings.json"))
    def test_math_lite(self) -> None:
        """Math-lite should render subscripts and symbols."""
        self.assertEqual(math_lite_to_unicode(r"Na_1 \in S"), "Na₁ ∈ S")
    def test_exchange_exports_send_recv(self) -> None:
        """One exchange should export both send and receive events."""
        project = CPSAGraphicalProject.new_default()
        protocol = project.active_protocol()
        diagram = project.active_diagram()
        assert protocol and diagram
        alice = ParticipantDraft(display_name="Alice", role_name="init")
        bob = ParticipantDraft(display_name="Bob", role_name="resp")
        project.semantic_model.participants.extend([alice, bob])
        protocol.participant_ids.extend([alice.id, bob.id])
        diagram.lifelines.extend([LifelineView(participant_id=alice.id, x_position=100.0), LifelineView(participant_id=bob.id, x_position=400.0)])
        term = TermDraft(text="(enc (cat Na A) (pubk B))", display_markup="{Na₁,A}_K_B")
        project.semantic_model.terms.append(term)
        exchange = MessageExchangeDraft(source_participant_id=alice.id, target_participant_id=bob.id, message_term_id=term.id, ordinal_hint=130.0)
        project.semantic_model.exchanges.append(exchange)
        protocol.message_exchange_ids.append(exchange.id)
        diagram.message_views.append(MessageExchangeView(exchange_id=exchange.id, source_lifeline_id=diagram.lifelines[0].id, target_lifeline_id=diagram.lifelines[1].id, y_position=130.0))
        output = generate_cpsa(project)
        self.assertIn("send", output)
        self.assertIn("recv", output)

if __name__ == "__main__":
    unittest.main()
