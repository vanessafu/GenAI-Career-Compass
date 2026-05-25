"""
Skill normalization engine backed by the MIND tech ontology.

Architecture (three-step as designed):
  Step 1  Entity resolution via synonym hash-table + Trie built from MIND's 3000+ nodes.
  Step 2  Each canonical node is enriched with transferability_scores and
          proficiency_levels (MIND JSON → skills-taxonomy schema migration).
  Step 3  Dimensionality reduction: every Library/Tool is clustered upward to a
          Framework domain so Gap Analysis runs on ~50 concepts, not 3300.

Setup (run once):
    python -m backend.scripts.build_ontology

At runtime the engine loads `data/ontology_cache.json`.  If the cache is absent
it falls back to built-in synonyms for the most common tech skills so the
system still works without the setup step.

This module is intentionally data-source agnostic — it normalises CV skills,
job posting skills, or any other free-text skill list identically.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger("CareerCompass.Normalization")

_DEFAULT_CACHE = (
    Path(__file__).resolve().parents[4] / "data" / "ontology_cache.json"
)

# ---------------------------------------------------------------------------
# Built-in synonym table (covers the most frequent tech aliases)
# Used as fallback when the MIND cache is absent, and always merged on top.
# ---------------------------------------------------------------------------
_BUILTIN_SYNONYMS: dict[str, str] = {
    # JavaScript ecosystem
    "js": "JavaScript", "javascript": "JavaScript", "ecmascript": "JavaScript",
    "ts": "TypeScript", "typescript": "TypeScript",
    "nodejs": "Node.js", "node": "Node.js", "node.js": "Node.js",
    "reactjs": "React", "react.js": "React",
    "vuejs": "Vue.js", "vue": "Vue.js", "vue.js": "Vue.js",
    "angularjs": "Angular", "angular.js": "Angular",
    "nextjs": "Next.js", "next.js": "Next.js",
    "nuxtjs": "Nuxt.js", "nuxt": "Nuxt.js",
    "nestjs": "NestJS", "nest.js": "NestJS",
    "expressjs": "Express.js", "express": "Express.js",
    # Python ecosystem
    "py": "Python", "python3": "Python", "python2": "Python",
    "fastapi": "FastAPI", "django": "Django", "flask": "Flask",
    # JVM
    "springboot": "Spring Boot", "spring-boot": "Spring Boot",
    "kotlin": "Kotlin", "scala": "Scala",
    # Data / ML
    "sklearn": "Scikit-learn", "scikit": "Scikit-learn",
    "tf": "TensorFlow", "tensorflow": "TensorFlow", "tensorflow2": "TensorFlow",
    "pytorch": "PyTorch", "torch": "PyTorch",
    "hf": "Hugging Face", "huggingface": "Hugging Face",
    "xgb": "XGBoost", "lgbm": "LightGBM",
    "ml": "Machine Learning", "ai": "Artificial Intelligence",
    "dl": "Deep Learning", "nlp": "Natural Language Processing",
    "cv": "Computer Vision",
    "llm": "Large Language Models", "llms": "Large Language Models",
    "rag": "Retrieval-Augmented Generation",
    # Databases
    "pg": "PostgreSQL", "postgres": "PostgreSQL", "postgresql": "PostgreSQL",
    "mysql": "MySQL", "sqlite": "SQLite",
    "mongo": "MongoDB", "mongodb": "MongoDB",
    "redis": "Redis", "es": "Elasticsearch", "elasticsearch": "Elasticsearch",
    "dynamodb": "DynamoDB",
    # Cloud / DevOps
    "aws": "AWS", "gcp": "Google Cloud Platform", "azure": "Microsoft Azure",
    "k8s": "Kubernetes", "kube": "Kubernetes",
    "docker": "Docker", "terraform": "Terraform", "ansible": "Ansible",
    "cicd": "CI/CD", "ci": "CI/CD", "cd": "CI/CD",
    "githubactions": "GitHub Actions", "gitlabci": "GitLab CI",
    # Misc
    "git": "Git", "github": "GitHub", "gitlab": "GitLab",
    "restapi": "REST API", "rest": "REST API", "restful": "REST API",
    "graphql": "GraphQL", "grpc": "gRPC",
    "kafka": "Apache Kafka", "spark": "Apache Spark", "flink": "Apache Flink",
    "linux": "Linux", "unix": "Linux",
    "bash": "Bash/Shell", "shell": "Bash/Shell",
    "oop": "Object-Oriented Programming",
    "go": "Go", "golang": "Go",
    "rust": "Rust", "cpp": "C++", "csharp": "C#", "dotnet": ".NET",
    "swift": "Swift", "flutter": "Flutter", "reactnative": "React Native",
    # SQL
    "sql": "SQL", "nosql": "NoSQL",
}

# ---------------------------------------------------------------------------
# Step 3 — Framework-level clustering (tool/library → domain)
# ~50 clusters; used by Gap Analysis instead of 3300-node full graph.
# ---------------------------------------------------------------------------
_TOOL_TO_FRAMEWORK: dict[str, str] = {
    # ML / AI
    "TensorFlow": "ML Frameworks", "PyTorch": "ML Frameworks",
    "Keras": "ML Frameworks", "JAX": "ML Frameworks",
    "Scikit-learn": "ML Libraries", "XGBoost": "ML Libraries",
    "LightGBM": "ML Libraries", "CatBoost": "ML Libraries",
    "Hugging Face": "NLP/LLM", "BERT": "NLP/LLM", "GPT": "NLP/LLM",
    "Large Language Models": "NLP/LLM",
    "Retrieval-Augmented Generation": "NLP/LLM",
    "Machine Learning": "ML/AI", "Deep Learning": "ML/AI",
    "Natural Language Processing": "NLP/LLM",
    "Computer Vision": "ML/AI", "Artificial Intelligence": "ML/AI",
    # Data Engineering
    "Pandas": "Data Engineering", "NumPy": "Data Engineering",
    "Polars": "Data Engineering", "Apache Spark": "Data Engineering",
    "Apache Kafka": "Data Streaming", "Apache Flink": "Data Streaming",
    "dbt": "Data Engineering", "Airflow": "Data Engineering",
    # Frontend
    "React": "Frontend Frameworks", "Vue.js": "Frontend Frameworks",
    "Angular": "Frontend Frameworks", "Svelte": "Frontend Frameworks",
    "Next.js": "Frontend Frameworks", "Nuxt.js": "Frontend Frameworks",
    "JavaScript": "Frontend Frameworks", "TypeScript": "Frontend Frameworks",
    # Backend
    "Django": "Backend Frameworks", "Flask": "Backend Frameworks",
    "FastAPI": "Backend Frameworks", "Node.js": "Backend Frameworks",
    "Spring Boot": "Backend Frameworks", "Express.js": "Backend Frameworks",
    "NestJS": "Backend Frameworks", "Laravel": "Backend Frameworks",
    "Ruby on Rails": "Backend Frameworks", ".NET": "Backend Frameworks",
    # Databases
    "PostgreSQL": "Relational Databases", "MySQL": "Relational Databases",
    "SQLite": "Relational Databases", "SQL": "Relational Databases",
    "MongoDB": "NoSQL Databases", "DynamoDB": "NoSQL Databases",
    "Cassandra": "NoSQL Databases", "NoSQL": "NoSQL Databases",
    "Redis": "In-Memory/Cache", "Elasticsearch": "Search Engines",
    # Cloud
    "AWS": "Cloud Platforms", "Microsoft Azure": "Cloud Platforms",
    "Google Cloud Platform": "Cloud Platforms",
    # DevOps
    "Docker": "Containerization", "Kubernetes": "Container Orchestration",
    "CI/CD": "DevOps", "Terraform": "Infrastructure as Code",
    "Ansible": "Infrastructure as Code",
    "GitHub Actions": "CI/CD Tools", "GitLab CI": "CI/CD Tools",
    "Jenkins": "CI/CD Tools",
    # Languages (kept at language level — already coarse enough)
    "Python": "Python", "Java": "Java", "Go": "Go",
    "Rust": "Rust", "C++": "C++", "C#": "C#",
    "Scala": "Scala", "Kotlin": "Kotlin", "Swift": "Swift",
    "Ruby": "Ruby",
    # Mobile
    "React Native": "Mobile Development", "Flutter": "Mobile Development",
    "iOS": "Mobile Development", "Android": "Mobile Development",
    # Misc
    "REST API": "API Development", "GraphQL": "API Development",
    "gRPC": "API Development",
    "Git": "Version Control", "GitHub": "Version Control",
    "Linux": "OS/Infrastructure", "Bash/Shell": "OS/Infrastructure",
    "Object-Oriented Programming": "Programming Paradigms",
}

# ---------------------------------------------------------------------------
# Default transferability matrix (framework-to-framework)
# Values are symmetric floats in [0, 1].  Populated from skills-taxonomy
# when the ontology cache is present; these defaults cover common paths.
# ---------------------------------------------------------------------------
_DEFAULT_TRANSFERABILITY: dict[str, dict[str, float]] = {
    "ML Frameworks": {
        "ML Libraries": 0.75, "NLP/LLM": 0.70, "ML/AI": 0.80,
        "Data Engineering": 0.55,
    },
    "Frontend Frameworks": {
        "Backend Frameworks": 0.45, "Mobile Development": 0.60,
        "API Development": 0.50,
    },
    "Backend Frameworks": {
        "Frontend Frameworks": 0.45, "API Development": 0.75,
        "Relational Databases": 0.60, "DevOps": 0.50,
    },
    "Python": {
        "ML Frameworks": 0.80, "Data Engineering": 0.80,
        "Backend Frameworks": 0.70, "NLP/LLM": 0.75,
    },
    "Java": {
        "Backend Frameworks": 0.75, "Android": 0.65, "Kotlin": 0.80,
    },
    "Cloud Platforms": {
        "DevOps": 0.70, "Infrastructure as Code": 0.65,
        "Container Orchestration": 0.65,
    },
}


# ---------------------------------------------------------------------------
# Trie implementation
# ---------------------------------------------------------------------------

class _TrieNode:
    __slots__ = ("children", "canonical", "is_end")

    def __init__(self) -> None:
        self.children: dict[str, "_TrieNode"] = {}
        self.canonical: Optional[str] = None
        self.is_end: bool = False


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class NormalizationEngine:
    """
    High-throughput skill entity-resolution engine.

    Resolution order (fastest first):
      1. Direct hash-table lookup  O(1)
      2. Trie traversal on normalised key  O(|key|)
      3. Title-case fallback (pass-through)

    All public methods are thread-safe for read access after __init__.
    """

    def __init__(self, cache_path: Optional[Path] = None) -> None:
        self._syn: dict[str, str] = {}          # normalised-key → canonical
        self._trie = _TrieNode()
        self._fw: dict[str, str] = {}           # canonical → framework domain
        self._transfer: dict[str, dict[str, float]] = {}
        self._prof: dict[str, list[str]] = {}   # canonical → proficiency levels

        self._load_builtins()

        path = cache_path or _DEFAULT_CACHE
        if path.exists():
            self._load_cache(path)
            logger.info("Loaded MIND ontology cache from %s", path)
        else:
            logger.warning(
                "MIND ontology cache not found at %s — built-in synonyms only. "
                "Run `python -m backend.scripts.build_ontology` to build it.",
                path,
            )

    # ------------------------------------------------------------------
    # Public API  (used by CV pipeline, job ETL, and gap analysis)
    # ------------------------------------------------------------------

    def normalize(self, skill: str) -> str:
        """Return the canonical form of a skill string."""
        if not skill:
            return skill
        key = _norm_key(skill)
        if key in self._syn:
            return self._syn[key]
        result = self._trie_lookup(key)
        if result:
            return result
        return skill.strip().title()

    def normalize_list(self, skills: list[str]) -> list[str]:
        """Normalize and deduplicate (preserve order)."""
        seen: set[str] = set()
        out: list[str] = []
        for s in skills:
            c = self.normalize(s)
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out

    def get_framework(self, skill: str) -> str:
        """Map a skill to its framework-level domain cluster."""
        canonical = self.normalize(skill)
        return self._fw.get(canonical, canonical)

    def get_transferability(self, from_skill: str, to_skill: str) -> float:
        """
        Transferability score [0, 1] between two skills (by framework).
        Higher = easier to bridge the gap.  Returns 0.3 as a neutral default.
        """
        f_from = self.get_framework(from_skill)
        f_to = self.get_framework(to_skill)
        if f_from == f_to:
            return 1.0
        # Check both directions (matrix may be non-symmetric in loaded data)
        score = self._transfer.get(f_from, {}).get(f_to)
        if score is None:
            score = self._transfer.get(f_to, {}).get(f_from, 0.3)
        return score

    def get_proficiency_levels(self, skill: str) -> list[str]:
        canonical = self.normalize(skill)
        return self._prof.get(canonical, ["Beginner", "Intermediate", "Advanced", "Expert"])

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load_builtins(self) -> None:
        for alias, canonical in _BUILTIN_SYNONYMS.items():
            key = _norm_key(alias)
            self._syn[key] = canonical
            self._trie_insert(key, canonical)
            # canonical maps to itself
            self._syn[_norm_key(canonical)] = canonical
        for canonical, framework in _TOOL_TO_FRAMEWORK.items():
            self._fw[canonical] = framework
        self._transfer = {k: dict(v) for k, v in _DEFAULT_TRANSFERABILITY.items()}

    def _load_cache(self, path: Path) -> None:
        with open(path, encoding="utf-8") as f:
            data: dict = json.load(f)

        # Step 1 — synonyms
        for entry in data.get("synonyms", []):
            canonical: str = entry["canonical"]
            self._syn[_norm_key(canonical)] = canonical
            for alias in entry.get("aliases", []):
                key = _norm_key(alias)
                self._syn[key] = canonical
                self._trie_insert(key, canonical)

        # Step 3 — framework clusters
        for entry in data.get("framework_clusters", []):
            fw: str = entry["framework"]
            for skill in entry.get("skills", []):
                self._fw[skill] = fw

        # Step 2 — transferability & proficiency (schema migration)
        for fw, targets in data.get("transferability_scores", {}).items():
            self._transfer.setdefault(fw, {}).update(targets)
        self._prof.update(data.get("proficiency_levels", {}))

    def _trie_insert(self, key: str, canonical: str) -> None:
        node = self._trie
        for ch in key:
            node = node.children.setdefault(ch, _TrieNode())
        node.is_end = True
        node.canonical = canonical

    def _trie_lookup(self, key: str) -> Optional[str]:
        node = self._trie
        for ch in key:
            if ch not in node.children:
                return None
            node = node.children[ch]
        return node.canonical if node.is_end else None


# ---------------------------------------------------------------------------
# Key normalisation helper
# ---------------------------------------------------------------------------

def _norm_key(text: str) -> str:
    """Lowercase, strip whitespace/hyphens/dots/slashes for collision-free lookup."""
    return re.sub(r"[\s\-\.\/\\#+]", "", text).lower()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_engine: Optional[NormalizationEngine] = None


def get_normalization_engine(cache_path: Optional[Path] = None) -> NormalizationEngine:
    """Return the singleton, initialising it on first call."""
    global _engine
    if _engine is None:
        _engine = NormalizationEngine(cache_path)
    return _engine


# Convenience wrappers — primary API for other modules
def normalize_skill(skill: str) -> str:
    return get_normalization_engine().normalize(skill)


def normalize_skills(skills: list[str]) -> list[str]:
    return get_normalization_engine().normalize_list(skills)
