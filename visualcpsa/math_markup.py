"""Standard-library math-lite markup support for diagram labels."""
from __future__ import annotations
import re

LATEX_SYMBOLS = {r"\forall": "∀", r"\exists": "∃", r"\in": "∈", r"\notin": "∉", r"\land": "∧", r"\lor": "∨", r"\implies": "⇒", r"\alpha": "α", r"\beta": "β"}
SUPERSCRIPT = str.maketrans({"0":"⁰","1":"¹","2":"²","3":"³","x":"ˣ","n":"ⁿ"})
SUBSCRIPT = str.maketrans({"0":"₀","1":"₁","2":"₂","3":"₃","a":"ₐ","x":"ₓ","n":"ₙ"})
SCRIPT_PATTERN = re.compile(r"(?P<operator>[\^_])(?:\{(?P<braced>[^{}]+)\}|(?P<single>[A-Za-z0-9+\-]))")


def translate_latex_symbols(markup: str) -> str:
    """Translate supported LaTeX-like commands to Unicode symbols."""
    assert isinstance(markup, str), "markup must be a string"
    translated = markup
    for command, symbol in sorted(LATEX_SYMBOLS.items(), key=lambda item: len(item[0]), reverse=True):
        translated = translated.replace(command, symbol)
    return translated


def translate_scripts(markup: str) -> str:
    """Translate simple superscript and subscript fragments to Unicode."""
    assert isinstance(markup, str), "markup must be a string"
    def replace_match(match: re.Match[str]) -> str:
        """Replace one regex match with Unicode script text."""
        operator = match.group("operator")
        content = match.group("braced") if match.group("braced") is not None else match.group("single")
        assert content is not None, "script content is required"
        return content.translate(SUPERSCRIPT if operator == "^" else SUBSCRIPT)
    result = SCRIPT_PATTERN.sub(replace_match, markup)
    assert isinstance(result, str), "script translation must return a string"
    return result


def math_lite_to_unicode(markup: str) -> str:
    """Convert supported math-lite markup to Unicode display text."""
    assert isinstance(markup, str), "markup must be a string"
    return translate_scripts(translate_latex_symbols(markup))
