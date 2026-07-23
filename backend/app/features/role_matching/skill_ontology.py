"""
Skill normalization + coverage using the MIND tech-skills ontology (MIT).

Vendor the ontology's aggregated file into your repo, e.g.:
    backend/data/__aggregated_skills.json.gz
(download from https://github.com/MIND-TechAI/MIND-tech-ontology , MIT-licensed)

Two ideas drive correct coverage:
  1. synonyms -> a single canonical skill name  (React.js / react js -> React)
  2. impliesKnowingSkills -> transitive closure  (Next.js -> React -> JavaScript)
     so a user who lists Next.js gets credit for React and JavaScript.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import logging
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from backend.app.features.role_matching.normalization import canon_skill, normalize_skill_key

logger = logging.getLogger("CareerCompass.SkillOntology")

ONTOLOGY_PATH = Path(__file__).parent.parent.parent.parent / "data" / "__aggregated_skills.json.gz"
ONTOLOGY_SHA256 = "5ba9aedda04a5052a6b8cdec796ab4350d507a2696986259541950351f4b2e14"

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

def _load_ontology(path: Path) -> dict | list:
    if not path.is_file():
        raise RuntimeError(f"Required MIND ontology file is missing: {path}")
    try:
        if path.suffix == ".gz":
            with gzip.open(path, "rb") as source:
                payload = source.read()
        else:
            payload = path.read_bytes()
    except OSError as exc:
        raise RuntimeError(f"MIND ontology file could not be read: {path}") from exc

    if path.resolve() == ONTOLOGY_PATH.resolve():
        actual = hashlib.sha256(payload).hexdigest()
        if actual != ONTOLOGY_SHA256:
            raise RuntimeError("MIND ontology checksum mismatch.")

    try:
        raw = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError(f"MIND ontology contains invalid JSON: {path}") from exc
    if not isinstance(raw, (dict, list)):
        raise RuntimeError(f"MIND ontology has an invalid root value: {path}")
    return raw


class SkillOntology:
    def __init__(self, path: Path = ONTOLOGY_PATH) -> None:
        self._canonical_by_alias: dict[str, str] = {}   # lowercased alias -> canonical name
        self._implies: dict[str, list[str]] = {}        # canonical -> direct implied skills
        self._domains: dict[str, list[str]] = {}         # canonical -> domain hints (technicalDomains first)
        self._closure_cache: dict[str, frozenset[str]] = {}

        ontology_path = Path(path)
        raw = _load_ontology(ontology_path)
        nodes = raw.values() if isinstance(raw, dict) else raw
        if any(not isinstance(node, dict) for node in nodes):
            raise RuntimeError(f"MIND ontology contains an invalid skill entry: {ontology_path}")

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

        if not self._canonical_by_alias:
            raise RuntimeError(f"MIND ontology contains no skills: {ontology_path}")
        logger.info("Loaded ontology: %d skills, %d aliases.",
                    len(self._implies), len(self._canonical_by_alias))

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

_ontology: Optional[SkillOntology] = None


def get_ontology() -> SkillOntology:
    """Module-level singleton, loaded on first call (like the embedder)."""
    global _ontology
    if _ontology is None:
        _ontology = SkillOntology()
    return _ontology


def canonical_skill_key(skill: str, alias_map: dict[str, str]) -> str:
    """Resolve the database alias map first, then MIND synonyms."""
    alias_key = canon_skill(skill, alias_map)
    mind_name = get_ontology().canonical(alias_key)
    return canon_skill(mind_name, alias_map) if mind_name else alias_key
