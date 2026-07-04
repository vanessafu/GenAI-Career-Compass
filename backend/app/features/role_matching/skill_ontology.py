"""
Skill normalization + coverage using the MIND tech-skills ontology (MIT).

Vendor the ontology's aggregated file into your repo, e.g.:
    data/__aggregated_skills.json
(download from https://github.com/MIND-TechAI/MIND-tech-ontology , MIT-licensed)

Two ideas drive correct coverage:
  1. synonyms -> a single canonical skill name  (React.js / react js -> React)
  2. impliesKnowingSkills -> transitive closure  (Next.js -> React -> JavaScript)
     so a user who lists Next.js gets credit for React and JavaScript.
"""
from __future__ import annotations

import json
import logging
import re
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from backend.app.features.role_matching.normalization import normalize_skill_key

logger = logging.getLogger("CareerCompass.SkillOntology")

ONTOLOGY_PATH = Path(__file__).parent.parent.parent.parent / "data" / "__aggregated_skills.json"

# Credit given when the user only holds a PREREQUISITE of the required skill
# (e.g. role wants Next.js, user has React). Tune to taste.
PARTIAL_CREDIT = 0.4

# Hop-decayed credit for skills implied by something the user explicitly holds
# (e.g. user has Next.js -> role wants React). hop=1 -> 0.65, hop=2 -> 0.52,
# hop=3 -> 0.416, floored at _MIN_CREDIT.
_HOP1_CREDIT = 0.65
_HOP_DECAY = 0.80
_MIN_CREDIT = 0.35
_MAX_HOPS = 3


def hop_confidence(hop: int) -> float:
    return max(_MIN_CREDIT, round(_HOP1_CREDIT * (_HOP_DECAY ** (hop - 1)), 4))


@dataclass(frozen=True)
class ImpliedSkill:
    hop: int
    via: str  # canonical name of the explicit skill the shortest path came from

# Split role skill strings on these only. NOTE: '/' is intentionally excluded so
# CI/CD, TCP/IP, I/O survive as single tokens.
_SPLIT = re.compile(r"[;,|\n\u2022]+")


def parse_raw_skills(raw: Optional[str]) -> list[str]:
    """career_roles.raw_skills (str) -> deduped list, order preserved."""
    if not raw:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for part in _SPLIT.split(raw):
        s = part.strip()
        key = s.lower()
        if s and key not in seen:
            seen.add(key)
            out.append(s)
    return out


def severity_from(credit: float) -> str:
    if credit >= 1.0:
        return "matched"
    if credit >= 0.5:
        return "low"
    if credit > 0.0:
        return "medium"
    return "high"


class SkillOntology:
    def __init__(self, path: Path = ONTOLOGY_PATH) -> None:
        self._canonical_by_alias: dict[str, str] = {}   # lowercased alias -> canonical name
        self._implies: dict[str, list[str]] = {}        # canonical -> direct implied skills
        self._domains: dict[str, list[str]] = {}         # canonical -> domain hints (technicalDomains first)
        self._closure_cache: dict[str, frozenset[str]] = {}
        self._exact_match_fallback = False

        ontology_path = Path(path)
        if not ontology_path.exists():
            self._exact_match_fallback = True
            logger.warning(
                "Skill ontology file %s not found. Falling back to exact skill matching.",
                ontology_path,
            )
            return

        raw = json.loads(ontology_path.read_text(encoding="utf-8"))
        nodes = raw.values() if isinstance(raw, dict) else raw  # tolerate list OR dict

        for node in nodes:
            name = node.get("name")
            if not name:
                continue
            self._implies[name] = list(node.get("impliesKnowingSkills") or [])
            aliases = set(node.get("synonyms") or [])
            aliases.add(name)
            for alias in aliases:
                key = normalize_skill_key(alias)
                if key:
                    self._canonical_by_alias[key] = name

            domains: list[str] = []
            seen_domains: set[str] = set()
            for domain in [*(node.get("technicalDomains") or []), *(node.get("associatedToApplicationDomains") or [])]:
                if domain and domain not in seen_domains:
                    seen_domains.add(domain)
                    domains.append(domain)
            if domains:
                self._domains[name] = domains

        logger.info("Loaded ontology: %d skills, %d aliases.",
                    len(self._implies), len(self._canonical_by_alias))

    def _fallback_key(self, skill: str) -> str:
        return re.sub(r"\s+", " ", (skill or "").strip()).casefold()

    # ---- normalization ----
    def canonical(self, skill: str) -> Optional[str]:
        """Resolve any surface form to its canonical skill name, or None if unknown."""
        return self._canonical_by_alias.get(normalize_skill_key(skill))

    def domain_hint(self, canonical_name: str) -> list[str]:
        """technicalDomains + associatedToApplicationDomains for canonical_name, deduped,
        technicalDomains first. [] if unresolved or the ontology has no domain data for it."""
        return self._domains.get(canonical_name, [])

    # ---- transitive implication ----
    def implied_closure(self, canonical_name: str) -> frozenset[str]:
        """Everything implied by knowing `canonical_name`, including itself."""
        cached = self._closure_cache.get(canonical_name)
        if cached is not None:
            return cached
        seen: set[str] = set()
        queue: deque[str] = deque([canonical_name])
        while queue:
            cur = queue.popleft()
            if cur in seen:
                continue
            seen.add(cur)
            for nxt in self._implies.get(cur, []):
                target = self.canonical(nxt) or nxt
                if target not in seen:
                    queue.append(target)
        frozen = frozenset(seen)
        self._closure_cache[canonical_name] = frozen
        return frozen

    def expand_user_skills(self, user_skills: Iterable[str]) -> dict[str, str]:
        """User skills + everything they imply -> {canonical: 'have' | 'implied'}."""
        effective: dict[str, str] = {}
        for s in user_skills:
            c = self.canonical(s)
            if not c:
                continue
            effective.setdefault(c, "have")
            for imp in self.implied_closure(c):
                effective.setdefault(imp, "implied")
        return effective

    def implied_with_hops(
        self, user_skills: Iterable[str], max_hops: int = _MAX_HOPS
    ) -> dict[str, ImpliedSkill]:
        """BFS from each canonical(user_skill), hop-capped at max_hops. Returns ONLY
        targets beyond the user's own explicit/canonical skills (those are excluded -
        hop distance starts at 1). On conflicting paths to the same target, keeps the
        shortest hop (first-seen wins ties)."""
        held: set[str] = set()
        for s in user_skills:
            c = self.canonical(s)
            if c:
                held.add(c)

        result: dict[str, ImpliedSkill] = {}
        for start in held:
            queue: deque[tuple[str, int]] = deque([(start, 0)])
            seen: set[str] = {start}
            while queue:
                cur, hop = queue.popleft()
                if hop >= max_hops:
                    continue
                for nxt in self._implies.get(cur, []):
                    target = self.canonical(nxt) or nxt
                    if target in seen:
                        continue
                    seen.add(target)
                    next_hop = hop + 1
                    if target not in held and (target not in result or next_hop < result[target].hop):
                        result[target] = ImpliedSkill(hop=next_hop, via=start)
                    queue.append((target, next_hop))
        return result

    # ---- coverage ----
    def compute_coverage(
        self, required_raw: Optional[str], user_skills: Iterable[str]
    ) -> tuple[float, list[str], list[dict]]:
        """
        Returns (weighted_coverage, matched_canonical_skills, gaps).
        Each gap: {required_skill, user_closest_skill, transferability, severity}.
        """
        user_skills = list(user_skills)
        if self._exact_match_fallback:
            required = parse_raw_skills(required_raw)
            if not required:
                return 0.0, [], []

            user_keys = {self._fallback_key(skill) for skill in user_skills}
            matched: list[str] = []
            gaps: list[dict] = []
            for req in required:
                if self._fallback_key(req) in user_keys:
                    matched.append(req)
                else:
                    gaps.append({
                        "required_skill": req,
                        "user_closest_skill": None,
                        "transferability": 0.0,
                        "severity": severity_from(0.0),
                    })
            return len(matched) / len(required), matched, gaps

        required = [self.canonical(r) or r for r in parse_raw_skills(required_raw)]
        required = list(dict.fromkeys(required))  # dedup, keep order
        if not required:
            return 0.0, [], []

        effective = self.expand_user_skills(user_skills)
        user_canon = {self.canonical(s) or s for s in user_skills}

        matched: list[str] = []
        gaps: list[dict] = []
        weight_sum = 0.0

        for req in required:
            if req in effective:                       # exact or implied -> full credit
                matched.append(req)
                weight_sum += 1.0
                continue
            # partial: does the user hold a prerequisite of req?
            prereqs = self.implied_closure(req) - {req}
            hit = user_canon & prereqs
            if hit:
                credit = PARTIAL_CREDIT
                weight_sum += credit
                closest = next(iter(hit))
                gaps.append({
                    "required_skill": req,
                    "user_closest_skill": closest,
                    "transferability": credit,
                    "severity": severity_from(credit),
                })
            else:                                       # true gap
                gaps.append({
                    "required_skill": req,
                    "user_closest_skill": None,
                    "transferability": 0.0,
                    "severity": severity_from(0.0),
                })

        coverage = weight_sum / len(required)
        return coverage, matched, gaps


_ontology: Optional[SkillOntology] = None


def get_ontology() -> SkillOntology:
    """Module-level singleton, loaded on first call (like the embedder)."""
    global _ontology
    if _ontology is None:
        _ontology = SkillOntology()
    return _ontology
