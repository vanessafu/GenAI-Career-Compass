from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.scripts.role_embeddings import (
    SKILL_RANK_ALPHA,
    LlmSkillEnhancement,
    RoleSkillEnhancement,
    _parse_llm_skill_enhancement,
    _split_raw_skills,
    compute_sort_skills,
    rank_role_skills,
    report_llm_failures,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


class SplitRawSkillsTests(unittest.TestCase):
    def test_splits_dedupes_and_preserves_order(self) -> None:
        result = _split_raw_skills("Java, PostgreSQL, RESTful APIs, java")

        self.assertEqual(result, ["Java", "PostgreSQL", "RESTful APIs"])

    def test_keeps_slash_tokens_intact(self) -> None:
        result = _split_raw_skills("CI/CD, TCP/IP, I/O")

        self.assertEqual(result, ["CI/CD", "TCP/IP", "I/O"])

    def test_empty_input_returns_empty_list(self) -> None:
        self.assertEqual(_split_raw_skills(None), [])
        self.assertEqual(_split_raw_skills(""), [])


class ParseLlmSkillEnhancementTests(unittest.TestCase):
    def test_parses_plain_json_reply(self) -> None:
        result = _parse_llm_skill_enhancement(
            '{"processed_job_title":"Backend Developer",'
            '"skill_domains":[{"domain":"Backend","skills":['
            '{"skill":"Python","tier":"essential","score":0.9},'
            '{"skill":"Docker","tier":"nice_to_have","score":0.2}]}]}'
        )

        self.assertEqual(result.processed_job_title, "Backend Developer")
        self.assertEqual(result.skill_scores, {"Python": 0.9, "Docker": 0.2})
        self.assertEqual(result.skill_domains, {"Python": "Backend", "Docker": "Backend"})

    def test_flattens_multiple_domains(self) -> None:
        result = _parse_llm_skill_enhancement(
            '{"processed_job_title":"Full Stack Developer",'
            '"skill_domains":['
            '{"domain":"Backend","skills":[{"skill":"FastAPI","tier":"essential","score":0.9}]},'
            '{"domain":"Frontend","skills":[{"skill":"React","tier":"essential","score":0.85}]}'
            ']}'
        )

        self.assertEqual(result.skill_scores, {"FastAPI": 0.9, "React": 0.85})
        self.assertEqual(result.skill_domains, {"FastAPI": "Backend", "React": "Frontend"})

    def test_strips_markdown_code_fence(self) -> None:
        result = _parse_llm_skill_enhancement(
            '```json\n{"processed_job_title":"SQL Developer",'
            '"skill_domains":[{"domain":"Databases","skills":['
            '{"skill":"SQL","tier":"essential","score":1.0}]}]}\n```'
        )

        self.assertEqual(result.skill_scores, {"SQL": 1.0})

    def test_accepts_skills_added_beyond_the_raw_list(self) -> None:
        # The whole point of enhancement: Gemini may add skills implied by the
        # title/description that weren't in the raw/legacy list at all.
        result = _parse_llm_skill_enhancement(
            '{"processed_job_title":"Platform Engineer",'
            '"skill_domains":[{"domain":"DevOps","skills":['
            '{"skill":"Python","tier":"essential","score":0.9},'
            '{"skill":"Kubernetes","tier":"important","score":0.5}]}]}'
        )

        self.assertEqual(result.skill_scores, {"Python": 0.9, "Kubernetes": 0.5})

    def test_missing_processed_job_title_is_none(self) -> None:
        result = _parse_llm_skill_enhancement(
            '{"skill_domains":[{"domain":"Backend","skills":['
            '{"skill":"Python","tier":"essential","score":0.9}]}]}'
        )

        self.assertIsNone(result.processed_job_title)
        self.assertEqual(result.skill_scores, {"Python": 0.9})

    def test_rejects_malformed_json(self) -> None:
        result = _parse_llm_skill_enhancement("not json at all")

        self.assertIsNone(result)

    def test_rejects_missing_skill_domains_key(self) -> None:
        result = _parse_llm_skill_enhancement('{"processed_job_title":"X","skills":[]}')

        self.assertIsNone(result)

    def test_rejects_empty_skill_domains(self) -> None:
        result = _parse_llm_skill_enhancement('{"processed_job_title":"X","skill_domains":[]}')

        self.assertIsNone(result)

    def test_clamps_out_of_range_scores(self) -> None:
        result = _parse_llm_skill_enhancement(
            '{"skill_domains":[{"domain":"Backend","skills":['
            '{"skill":"Python","tier":"essential","score":1.5}]}]}'
        )

        self.assertEqual(result.skill_scores, {"Python": 1.0})


class RankRoleSkillsTests(unittest.TestCase):
    def test_sort_skills_carries_the_domain_from_each_skill_group(self) -> None:
        class FakeEmbedder:
            def encode_documents(self, texts: list[str]) -> list[list[float]]:
                # [description, "FastAPI", "React"]
                return [[1.0, 0.0], [0.9, 0.1], [0.2, 0.8]]

        with (
            patch(
                "backend.scripts.role_embeddings.enhance_and_rank_skills_with_llm",
                return_value=LlmSkillEnhancement(
                    processed_job_title="Full Stack Developer",
                    skill_scores={"FastAPI": 0.9, "React": 0.85},
                    skill_domains={"FastAPI": "Backend", "React": "Frontend"},
                ),
            ),
            patch(
                "backend.scripts.role_embeddings.get_embedder",
                return_value=FakeEmbedder(),
            ),
        ):
            result = rank_role_skills(1, "Full Stack Developer", "Builds features.", ["FastAPI", "React"])

        self.assertEqual(
            {item["skill"]: item["domain"] for item in result.sort_skills},
            {"FastAPI": "Backend", "React": "Frontend"},
        )

    def test_blends_llm_and_embedding_scores_and_sorts_descending(self) -> None:
        class FakeEmbedder:
            def encode_documents(self, texts: list[str]) -> list[list[float]]:
                # [description, "Python", "Docker"]
                return [[1.0, 0.0], [0.9, 0.1], [0.1, 0.9]]

        with (
            patch(
                "backend.scripts.role_embeddings.enhance_and_rank_skills_with_llm",
                return_value=LlmSkillEnhancement(
                    processed_job_title="Backend Developer",
                    skill_scores={"Python": 0.9, "Docker": 0.1},
                ),
            ),
            patch(
                "backend.scripts.role_embeddings.get_embedder",
                return_value=FakeEmbedder(),
            ),
        ):
            result = rank_role_skills(1, "Backend Developer", "Builds APIs.", ["Python", "Docker"])

        self.assertEqual(result.processed_job_title, "Backend Developer")
        self.assertEqual([item["skill"] for item in result.sort_skills], ["Python", "Docker"])
        self.assertEqual(result.processed_skills, ["Python", "Docker"])
        # final = SKILL_RANK_ALPHA * llm + (1 - SKILL_RANK_ALPHA) * emb
        self.assertAlmostEqual(
            result.sort_skills[0]["score"], SKILL_RANK_ALPHA * 0.9 + (1 - SKILL_RANK_ALPHA) * 0.9, places=4
        )
        self.assertAlmostEqual(
            result.sort_skills[1]["score"], SKILL_RANK_ALPHA * 0.1 + (1 - SKILL_RANK_ALPHA) * 0.1, places=4
        )

    def test_uses_enhanced_skill_set_even_when_it_differs_from_raw_input(self) -> None:
        # Gemini can drop a vague raw skill and add a more specific implied one;
        # the ranked output should reflect the enhanced set, not the raw input.
        class FakeEmbedder:
            def encode_documents(self, texts: list[str]) -> list[list[float]]:
                # [description, "Python", "Kubernetes"]
                return [[1.0, 0.0], [0.8, 0.2], [0.3, 0.7]]

        with (
            patch(
                "backend.scripts.role_embeddings.enhance_and_rank_skills_with_llm",
                return_value=LlmSkillEnhancement(
                    processed_job_title=None,
                    skill_scores={"Python": 0.9, "Kubernetes": 0.6},
                ),
            ),
            patch(
                "backend.scripts.role_embeddings.get_embedder",
                return_value=FakeEmbedder(),
            ),
        ):
            result = rank_role_skills(1, "Platform Engineer", "Runs infra.", ["Programming languages"])

        self.assertEqual({item["skill"] for item in result.sort_skills}, {"Python", "Kubernetes"})
        self.assertEqual(set(result.processed_skills), {"Python", "Kubernetes"})

    def test_skips_role_without_embedding_or_retry_when_llm_is_unusable(self) -> None:
        with (
            patch(
                "backend.scripts.role_embeddings.enhance_and_rank_skills_with_llm",
                return_value=None,
            ) as llm_mock,
            patch("backend.scripts.role_embeddings.get_embedder") as embedder_mock,
        ):
            result = rank_role_skills(1, "Backend Developer", "Builds APIs.", ["Python"])

        # LLM missing -> skip outright: no embedding fallback call, no retry
        # (called exactly once), and the role is marked llm_failed for
        # --retry-failures instead of getting a low-quality partial ranking.
        self.assertEqual(result, RoleSkillEnhancement(llm_failed=True))
        llm_mock.assert_called_once()
        embedder_mock.assert_not_called()

    def test_no_raw_skills_returns_empty_enhancement_without_calling_apis(self) -> None:
        with (
            patch("backend.scripts.role_embeddings.enhance_and_rank_skills_with_llm") as llm_mock,
            patch("backend.scripts.role_embeddings.get_embedder") as embedder_mock,
        ):
            result = rank_role_skills(1, "Backend Developer", "Builds APIs.", [])

        self.assertEqual(result, RoleSkillEnhancement())
        llm_mock.assert_not_called()
        embedder_mock.assert_not_called()


class ComputeSortSkillsTests(unittest.TestCase):
    def test_ranks_each_role_one_at_a_time(self) -> None:
        with patch("backend.scripts.role_embeddings.rank_role_skills") as rank_mock:
            rank_mock.side_effect = lambda role_id, title, description, skills: RoleSkillEnhancement(
                processed_job_title=title,
                sort_skills=[{"skill": skill, "score": 1.0} for skill in skills],
                processed_skills=list(skills),
            )

            result = compute_sort_skills(
                ids=[1, 2],
                titles=["Backend Developer", "Frontend Developer"],
                descriptions=["Builds APIs.", "Builds UIs."],
                cleaned_skills=[["Python"], ["CSS"]],
            )

        self.assertEqual(
            result,
            {
                1: RoleSkillEnhancement(
                    processed_job_title="Backend Developer",
                    sort_skills=[{"skill": "Python", "score": 1.0}],
                    processed_skills=["Python"],
                ),
                2: RoleSkillEnhancement(
                    processed_job_title="Frontend Developer",
                    sort_skills=[{"skill": "CSS", "score": 1.0}],
                    processed_skills=["CSS"],
                ),
            },
        )
        self.assertEqual(
            [call.args for call in rank_mock.call_args_list],
            [
                (1, "Backend Developer", "Builds APIs.", ["Python"]),
                (2, "Frontend Developer", "Builds UIs.", ["CSS"]),
            ],
        )


class ReportLlmFailuresTests(unittest.TestCase):
    def test_writes_failed_role_ids_as_retryable_arg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            failures_file = Path(tmp_dir) / "last_llm_failures.txt"
            with patch("backend.scripts.role_embeddings.LLM_FAILURES_FILE", failures_file):
                failed = report_llm_failures(
                    {
                        1: RoleSkillEnhancement(llm_failed=False),
                        2: RoleSkillEnhancement(llm_failed=True),
                        3: RoleSkillEnhancement(llm_failed=True),
                    }
                )

            self.assertEqual(failed, [2, 3])
            self.assertEqual(failures_file.read_text(encoding="utf-8"), "2,3\n")

    def test_no_failures_removes_stale_file_and_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            failures_file = Path(tmp_dir) / "last_llm_failures.txt"
            failures_file.write_text("9,10\n", encoding="utf-8")
            with patch("backend.scripts.role_embeddings.LLM_FAILURES_FILE", failures_file):
                failed = report_llm_failures({1: RoleSkillEnhancement(llm_failed=False)})

            self.assertEqual(failed, [])
            self.assertFalse(failures_file.exists())


class SortSkillsSchemaTests(unittest.TestCase):
    def test_role_embedding_script_writes_enhancement_columns(self) -> None:
        source = (REPO_ROOT / "backend" / "scripts" / "role_embeddings.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("ADD COLUMN IF NOT EXISTS sort_skills jsonb", source)
        self.assertIn("ADD COLUMN IF NOT EXISTS processed_job_title text", source)
        self.assertIn("ADD COLUMN IF NOT EXISTS processed_skills jsonb", source)
        self.assertIn("sort_skills = v.sort_skills::jsonb", source)
        self.assertIn("processed_job_title = v.processed_job_title", source)
        self.assertIn("processed_skills = v.processed_skills::jsonb", source)


if __name__ == "__main__":
    unittest.main()
