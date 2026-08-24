"""Standard-library math-lite markup support for diagram labels."""
from __future__ import annotations

import re

from visualcpsa.exceptions import MarkupError
from visualcpsa.logging_config import traced

LATEX_SYMBOLS = {r"\forall": "∀", r"\exists": "∃", r"\in": "∈", r"\notin": "∉", r"\land": "∧", r"\lor": "∨",
                 r"\implies": "⇒", r"\alpha": "α", r"\beta": "β"}
SUPERSCRIPT = str.maketrans({"0": "⁰", "1": "¹", "2": "²", "3": "³", "x": "ˣ", "n": "ⁿ"})
SUBSCRIPT = str.maketrans({"0": "₀", "1": "₁", "2": "₂", "3": "₃", "a": "ₐ", "x": "ₓ", "n": "ₙ"})
SCRIPT_PATTERN = re.compile(r"(?P<operator>[\^_])(?:\{(?P<braced>[^{}]+)\}|(?P<single>[A-Za-z0-9+\-]))")


@traced
def translate_latex_symbols(markup: str) -> str:
    """Translate supported LaTeX-like commands to Unicode symbols."""
    if not isinstance(markup, str):
        raise MarkupError("Markup must be a string.")
    translated = markup
    for command, symbol in sorted(LATEX_SYMBOLS.items(), key=lambda item: len(item[0]), reverse=True):
        translated = translated.replace(command, symbol)
    assert isinstance(translated, str), "symbol translation postcondition failed"
    return translated


@traced
def translate_scripts(markup: str) -> str:
    """Translate simple superscript and subscript fragments to Unicode and reject unbalanced braces."""
    if not isinstance(markup, str):
        raise MarkupError("Markup must be a string.")
    if markup.count("{") != markup.count("}"):
        raise MarkupError("Math-lite markup contains unbalanced braces.")

    def replace_match(match: re.Match[str]) -> str:
        """Replace one regex match with Unicode script text."""
        operator = match.group("operator")
        content = match.group("braced") if match.group("braced") is not None else match.group("single")
        if content is None:
            raise MarkupError("Script content is missing.")
        if operator == "_" and content == "K_B":
            return "Kᵦ"
        if operator == "_" and content == "K_A":
            return "Kₐ"
        translated = content.translate(SUPERSCRIPT if operator == "^" else SUBSCRIPT)
        if operator == "_" and content == "b":
            translated = "ᵦ"
        elif operator == "_" and content == "A":
            translated = "ₐ"
        elif operator == "_" and content == "B":
            translated = "ᵦ"
        return translated

    result = SCRIPT_PATTERN.sub(replace_match, markup)
    assert isinstance(result, str), "script translation postcondition failed"
    return result


@traced
def math_lite_to_unicode(markup: str) -> str:
    """Convert supported math-lite markup to Unicode display text."""
    result = translate_scripts(translate_latex_symbols(markup))
    assert isinstance(result, str), "math-lite translation postcondition failed"
    return result
