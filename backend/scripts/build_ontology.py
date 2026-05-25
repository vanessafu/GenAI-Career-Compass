"""
MIND tech-ontology cache builder.

Steps
-----
1. Clone (or pull) MIND-TechAI/MIND-tech-ontology into a temp directory.
2. Walk the JSON nodes and extract: canonical name, aliases/synonyms,
   parent category, and skill type (Language / Framework / Library / Tool).
3. Optionally pull tanova-ai/skills-taxonomy to enrich nodes with
   transferability_scores and proficiency_levels (Step 2 schema migration).
4. Cluster every Library/Tool upward to Framework level (Step 3 reduction).
5. Write data/ontology_cache.json.

Usage
-----
    python -m backend.scripts.build_ontology
    python -m backend.scripts.build_ontology --no-taxonomy   # skip skills-taxonomy
    python -m backend.scripts.build_ontology --output path/to/cache.json

Repos cloned into:  /tmp/career_compass_repos/  (re-used on subsequent runs)
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("CareerCompass.BuildOntology")

# ---------------------------------------------------------------------------
# Output path
# ---------------------------------------------------------------------------

_DEFAULT_OUTPUT = (
    Path(__file__).resolve().parents[2] / "data" / "ontology_cache.json"
)

_REPO_DIR = Path("/tmp/career_compass_repos")

# Canonical repo URLs (primary source = MIND, supplementary = skills-taxonomy)
_MIND_REPO = "https://github.com/MIND-TechAI/MIND-tech-ontology.git"
_TAXONOMY_REPO = "https://github.com/tanova-ai/skills-taxonomy.git"


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def _clone_or_pull(url: str, dest: Path) -> Path:
    """Clone repo if absent, otherwise git pull. Returns the local path."""
    import git  # gitpython

    if dest.exists():
        logger.info("Updating existing repo at %s", dest)
        repo = git.Repo(dest)
        repo.remotes.origin.pull()
    else:
        logger.info("Cloning %s → %s", url, dest)
        dest.mkdir(parents=True, exist_ok=True)
        git.Repo.clone_from(url, dest, depth=1)
    return dest


# ---------------------------------------------------------------------------
# MIND ontology parser
# ---------------------------------------------------------------------------

def _parse_mind(repo_path: Path) -> list[dict]:
    """
    Walk all JSON files under the MIND repo and extract skill nodes.

    Expected MIND JSON structure (each file may vary slightly):
      {
        "name": "React",
        "aliases": ["ReactJS", "React.js"],
        "type": "Framework",          # Language | Framework | Library | Tool
        "parent": "JavaScript",
        "category": "Frontend"
      }
    or nested arrays/objects.  We handle both flat and tree formats.
    """
    entries: list[dict] = []

    for json_file in sorted(repo_path.rglob("*.json")):
        # Skip package / config files
        if json_file.name in ("package.json", "package-lock.json", "tsconfig.json"):
            continue
        try:
            with open(json_file, encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        # The repo may store nodes as a top-level list or dict
        nodes = data if isinstance(data, list) else data.get("skills", data.get("nodes", [data]))
        if not isinstance(nodes, list):
            nodes = [nodes]

        for node in nodes:
            if not isinstance(node, dict):
                continue
            name = node.get("name") or node.get("title") or node.get("label")
            if not name or not isinstance(name, str):
                continue

            aliases: list[str] = []
            raw_aliases = node.get("aliases") or node.get("synonyms") or node.get("alternativeNames") or []
            if isinstance(raw_aliases, list):
                aliases = [str(a) for a in raw_aliases if a]
            elif isinstance(raw_aliases, str):
                aliases = [a.strip() for a in raw_aliases.split(",") if a.strip()]

            entries.append({
                "canonical": name.strip(),
                "aliases": aliases,
                "type": node.get("type") or node.get("skillType") or "Unknown",
                "parent": node.get("parent") or node.get("parentSkill") or "",
                "category": node.get("category") or node.get("domain") or "",
            })

    logger.info("Parsed %d skill nodes from MIND ontology.", len(entries))
    return entries


# ---------------------------------------------------------------------------
# Framework clustering  (Step 3)
# ---------------------------------------------------------------------------

# Skill types that should be clustered upward to their parent Framework
_CLUSTER_UP = {"Library", "Tool", "Plugin", "Package", "Module"}

def _build_framework_clusters(entries: list[dict]) -> list[dict]:
    """
    Map Library/Tool nodes to their nearest Framework ancestor.
    Returns a list of {framework, skills} dicts.
    """
    # Build parent lookup
    parent_map: dict[str, str] = {}
    type_map: dict[str, str] = {}
    for e in entries:
        parent_map[e["canonical"]] = e.get("parent", "")
        type_map[e["canonical"]] = e.get("type", "Unknown")

    def find_framework(name: str, depth: int = 0) -> str:
        """Walk up the parent chain until we hit a Framework or Language."""
        if depth > 6:
            return name
        skill_type = type_map.get(name, "Unknown")
        if skill_type in ("Framework", "Language", "Platform"):
            return name
        parent = parent_map.get(name, "")
        if not parent or parent == name:
            return name
        return find_framework(parent, depth + 1)

    clusters: dict[str, list[str]] = {}
    for e in entries:
        canonical = e["canonical"]
        if e.get("type") in _CLUSTER_UP:
            fw = find_framework(canonical)
            clusters.setdefault(fw, []).append(canonical)

    return [{"framework": fw, "skills": skills} for fw, skills in clusters.items()]


# ---------------------------------------------------------------------------
# skills-taxonomy enrichment  (Step 2 schema migration)
# ---------------------------------------------------------------------------

def _parse_taxonomy(repo_path: Path) -> tuple[dict, dict]:
    """
    Extract transferability_scores and proficiency_levels from skills-taxonomy.
    Returns (transferability_dict, proficiency_dict).
    """
    transferability: dict[str, dict[str, float]] = {}
    proficiency: dict[str, list[str]] = {}

    for json_file in sorted(repo_path.rglob("*.json")):
        if json_file.name in ("package.json",):
            continue
        try:
            with open(json_file, encoding="utf-8", errors="ignore") as f:
                data: Any = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        skills = data if isinstance(data, list) else data.get("skills", [])
        if not isinstance(skills, list):
            continue

        for skill in skills:
            if not isinstance(skill, dict):
                continue
            name: str = skill.get("name") or skill.get("title") or ""
            if not name:
                continue

            # Proficiency levels
            levels = skill.get("proficiency_levels") or skill.get("levels")
            if isinstance(levels, list):
                proficiency[name] = [str(l) for l in levels]

            # Transferability
            trans = skill.get("transferability") or skill.get("transferability_scores")
            if isinstance(trans, dict):
                transferability[name] = {
                    k: float(v) for k, v in trans.items()
                    if isinstance(v, (int, float))
                }

    logger.info(
        "Taxonomy: %d transferability entries, %d proficiency entries.",
        len(transferability), len(proficiency),
    )
    return transferability, proficiency


# ---------------------------------------------------------------------------
# Cache writer
# ---------------------------------------------------------------------------

def _write_cache(
    entries: list[dict],
    clusters: list[dict],
    transferability: dict,
    proficiency: dict,
    output: Path,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)

    # Deduplicate synonym entries
    seen_canonical: dict[str, set[str]] = {}
    for e in entries:
        c = e["canonical"]
        seen_canonical.setdefault(c, set()).update(e.get("aliases", []))

    synonyms = [
        {"canonical": c, "aliases": sorted(aliases)}
        for c, aliases in seen_canonical.items()
    ]

    cache = {
        "synonyms": synonyms,
        "framework_clusters": clusters,
        "transferability_scores": transferability,
        "proficiency_levels": proficiency,
    }

    with open(output, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

    logger.info(
        "Cache written to %s  (%d synonyms, %d clusters).",
        output, len(synonyms), len(clusters),
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build(output: Path = _DEFAULT_OUTPUT, use_taxonomy: bool = True) -> None:
    _REPO_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1 — clone / update MIND ontology
    mind_path = _clone_or_pull(_MIND_REPO, _REPO_DIR / "MIND-tech-ontology")
    entries = _parse_mind(mind_path)

    if not entries:
        logger.warning(
            "No entries parsed from MIND repo — the repo structure may have changed. "
            "Falling back to built-in synonym table only."
        )

    # Step 3 — framework clustering
    clusters = _build_framework_clusters(entries)
    logger.info("Built %d framework clusters.", len(clusters))

    transferability: dict = {}
    proficiency: dict = {}

    # Step 2 — schema migration via skills-taxonomy
    if use_taxonomy:
        try:
            taxonomy_path = _clone_or_pull(_TAXONOMY_REPO, _REPO_DIR / "skills-taxonomy")
            transferability, proficiency = _parse_taxonomy(taxonomy_path)
        except Exception as exc:
            logger.warning("skills-taxonomy enrichment failed (%s) — skipping.", exc)

    _write_cache(entries, clusters, transferability, proficiency, output)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s  %(message)s",
    )
    parser = argparse.ArgumentParser(description="Build MIND ontology cache.")
    parser.add_argument(
        "--output", type=Path, default=_DEFAULT_OUTPUT,
        help="Output path for ontology_cache.json",
    )
    parser.add_argument(
        "--no-taxonomy", action="store_true",
        help="Skip skills-taxonomy enrichment (transferability / proficiency data)",
    )
    args = parser.parse_args()
    try:
        build(output=args.output, use_taxonomy=not args.no_taxonomy)
    except Exception as exc:
        logger.error("Build failed: %s", exc, exc_info=True)
        sys.exit(1)
