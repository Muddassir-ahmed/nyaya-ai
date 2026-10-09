"""Narrow contradiction checks for explicitly stated penalty clauses.

This supplements lexical grounding; it is not a general legal entailment
checker. Ambiguous rule associations are left to the other validators.
"""
import re
from difflib import SequenceMatcher

from app.schemas.legal_evidence import LegalEvidence

_CONSEQUENCE = re.compile(
    r"\b(?:shall\s+be\s+punished\s+with|may\s+be\s+punished\s+with|"
    r"(?:the\s+)?punishment\s+(?:is|may\s+include))\b", re.I
)
_UNITS = re.compile(
    r"(?<=[.!?])\s+|\n+|(?=\bprovided\s+that\b)|(?=\bin\s+case\s+of\b)", re.I
)
_BOUND = re.compile(
    r"\b(?:up\s+to|extend\s*to|not\s+exceeding)\s+"
    r"(?P<number>\d+|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)"
    r"\s+(?P<unit>years?|months?|days?)\b", re.I
)
_NUMBERS = {name: n for n, name in enumerate(
    'zero one two three four five six seven eight nine ten eleven twelve '
    'thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty'.split()
)}
_GENERIC = set('a an and are as at be been being by for from has have he her him his '
               'if in into is it its of on or that the their them then this to under '
               'upon was were where which who whoever with shall may person persons '
               'section subsection act cases case any such order'.split())
_PENALTIES = {'imprisonment', 'fine', 'community', 'service'}


def _tokens(text: str) -> set[str]:
    return set(re.findall(r'[a-z]+|\d+', text.lower())) - _GENERIC


def _matches(left: str, right: str) -> bool:
    return left == right or (
        min(len(left), len(right)) >= 5
        and SequenceMatcher(None, left, right).ratio() >= 0.82
    )


def _bounds(text: str) -> set[tuple[int, str]]:
    values = set()
    for match in _BOUND.finditer(text):
        number = match['number'].lower()
        value = int(number) if number.isdigit() else _NUMBERS[number]
        unit = match['unit'].lower().rstrip('s')
        if unit == 'year':
            value, unit = value * 12, 'month'
        values.add((value, unit))
    return values


def _rules(text: str):
    for unit in _UNITS.split(text):
        markers = list(_CONSEQUENCE.finditer(unit))
        # Do not infer clause boundaries when a unit has several consequences.
        if len(markers) != 1:
            continue
        marker = markers[0]
        condition = unit[:marker.start()]
        consequence = unit[marker.end():]
        yield condition, marker.group().lower(), consequence


def penalty_contradiction(claim: str, evidence: list[LegalEvidence]) -> str | None:
    """Return a reason only for a confidently associated, explicit contradiction."""
    source_rules = [rule for item in evidence for rule in _rules(item.content)]
    modality_reason = None
    for condition, modality, consequence in _rules(claim):
        # Each independently introduced alternative must support the shared
        # consequence. Do not split ordinary lists such as death, hurt or fear.
        branches = re.split(r'\bor\s+if\b', condition, flags=re.I)
        for branch in branches:
            tokens = _tokens(branch)
            if len(tokens) < 2:
                continue
            candidates = []
            for source_condition, source_modality, source_consequence in source_rules:
                source_tokens = _tokens(source_condition)
                matched = sum(any(_matches(t, s) for s in source_tokens) for t in tokens)
                score = matched / len(tokens)
                shared_penalty = _tokens(consequence) & _tokens(source_consequence) & _PENALTIES
                if matched >= 2 and score >= 0.60 and shared_penalty:
                    candidates.append((score, source_modality, source_consequence))
            if not candidates:
                continue
            best_score = max(c[0] for c in candidates)
            best = [c for c in candidates if c[0] == best_score]
            # Only reject if all equally plausible source rules contradict it.
            claimed_bounds = _bounds(consequence)
            if claimed_bounds and all(
                _bounds(c[2])
                and {unit for _, unit in claimed_bounds}
                == {unit for _, unit in _bounds(c[2])}
                and not claimed_bounds <= _bounds(c[2])
                for c in best
            ):
                return (
                    'A stated maximum penalty duration does not match the '
                    'cited evidence for one of its stated circumstances.'
                )
            if 'may' in modality and all(
                c[1].startswith('shall')
                and not re.search(r'\bor\b', c[2], re.I)
                for c in best
            ):
                modality_reason = (
                    'A mandatory penalty consequence in the cited evidence '
                    'was presented as discretionary.'
                )
    return modality_reason
