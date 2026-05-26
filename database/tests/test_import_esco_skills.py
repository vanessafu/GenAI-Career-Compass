import csv
import importlib.util
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "import_esco_skills.py"
spec = importlib.util.spec_from_file_location("import_esco_skills", SCRIPT_PATH)
import_esco_skills = importlib.util.module_from_spec(spec)
sys.modules["import_esco_skills"] = import_esco_skills
spec.loader.exec_module(import_esco_skills)


class FakeClient:
    def __init__(self, occupation_uris=None):
        self.occupation_uris = set(occupation_uris or [])
        self.skills = {}
        self.relations = {}
        self.inserted_skills = []
        self.updated_skills = []
        self.inserted_relations = []
        self.updated_relations = []

    def list_esco_occupation_uris(self):
        return set(self.occupation_uris)

    def list_existing_skills(self, skill_uris):
        return {
            uri: dict(self.skills[uri])
            for uri in skill_uris
            if uri in self.skills
        }

    def upsert_skills(self, skills, force=False):
        stats = import_esco_skills.ImportStats()
        for skill in skills:
            payload = skill.to_payload()
            existing = self.skills.get(skill.esco_skill_uri)
            if existing is None:
                self.skills[skill.esco_skill_uri] = payload
                self.inserted_skills.append(payload)
                stats.skills_inserted += 1
            elif force:
                self.skills[skill.esco_skill_uri] = payload
                self.updated_skills.append(payload)
                stats.skills_updated += 1
            else:
                stats.skills_reused += 1
        return stats

    def list_existing_relations(self, relations):
        existing = {}
        for relation in relations:
            key = relation.identity_key()
            if key in self.relations:
                existing[key] = dict(self.relations[key])
        return existing

    def upsert_relations(self, relations, force=False):
        stats = import_esco_skills.ImportStats()
        for relation in relations:
            key = relation.identity_key()
            payload = relation.to_payload()
            existing = self.relations.get(key)
            if existing is None:
                self.relations[key] = payload
                self.inserted_relations.append(payload)
                stats.relations_inserted += 1
            elif force:
                self.relations[key] = payload
                self.updated_relations.append(payload)
                stats.relations_updated += 1
            else:
                stats.relations_reused += 1
        return stats


class ImportEscoSkillsTests(unittest.TestCase):
    def write_csv(self, filename, rows, fieldnames):
        directory = TemporaryDirectory()
        path = Path(directory.name) / filename
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        self.addCleanup(directory.cleanup)
        return path

    def test_parse_filters_relations_to_existing_occupations_and_collects_skill_uris(self):
        relations_path = self.write_csv(
            "occupationSkillRelations_en.csv",
            [
                {
                    "occupationUri": " uri:occupation:included ",
                    "skillUri": " uri:skill:one ",
                    "relationType": " ESSENTIAL ",
                    "skillType": "skill/competence",
                },
                {
                    "occupationUri": "uri:occupation:included",
                    "skillUri": "uri:skill:two",
                    "relationType": "optional",
                    "skillType": "knowledge",
                },
                {
                    "occupationUri": "uri:occupation:other",
                    "skillUri": "uri:skill:ignored",
                    "relationType": "essential",
                    "skillType": "skill/competence",
                },
                {
                    "occupationUri": "",
                    "skillUri": "uri:skill:missing-occupation",
                    "relationType": "optional",
                    "skillType": "skill/competence",
                },
                {
                    "occupationUri": "uri:occupation:included",
                    "skillUri": "",
                    "relationType": "essential",
                    "skillType": "skill/competence",
                },
                {
                    "occupationUri": "uri:occupation:included",
                    "skillUri": "uri:skill:weird",
                    "relationType": "broader",
                    "skillType": "knowledge",
                },
            ],
            ["occupationUri", "skillUri", "relationType", "skillType"],
        )

        result = import_esco_skills.parse_relations_csv(
            relations_path,
            {"uri:occupation:included"},
        )

        self.assertEqual(result.stats.total_relation_rows_read, 6)
        self.assertEqual(result.stats.relation_rows_linked_to_existing_occupations, 3)
        self.assertEqual(
            result.needed_skill_uris,
            {"uri:skill:one", "uri:skill:two", "uri:skill:weird"},
        )
        self.assertEqual(
            [relation.relation_type for relation in result.relations],
            ["essential", "optional", "broader"],
        )
        self.assertEqual(result.relation_type_counts["essential"], 1)
        self.assertEqual(result.relation_type_counts["optional"], 1)
        self.assertEqual(result.unusual_relation_types, {"broader"})
        self.assertEqual(
            [row.skip_reason for row in result.review_rows],
            [
                "",
                "",
                "occupation_not_imported",
                "missing_occupation_uri",
                "missing_skill_uri",
                "",
            ],
        )

    def test_parse_supports_human_readable_relation_columns(self):
        relations_path = self.write_csv(
            "occupationSkillRelations_en.csv",
            [
                {
                    "occupation concept URI": "uri:occupation:included",
                    "skill concept URI": "uri:skill:one",
                    "Relationship type": "Optional",
                    "skillType": "knowledge",
                }
            ],
            [
                "occupation concept URI",
                "skill concept URI",
                "Relationship type",
                "skillType",
            ],
        )

        result = import_esco_skills.parse_relations_csv(
            relations_path,
            {"uri:occupation:included"},
        )

        self.assertEqual(len(result.relations), 1)
        relation = result.relations[0]
        self.assertEqual(relation.esco_uri, "uri:occupation:included")
        self.assertEqual(relation.esco_skill_uri, "uri:skill:one")
        self.assertEqual(relation.relation_type, "optional")

    def test_parse_skills_imports_only_needed_skills_and_reports_missing(self):
        skills_path = self.write_csv(
            "skills_en.csv",
            [
                {
                    "conceptUri": " uri:skill:one ",
                    "conceptType": "Skill",
                    "skillType": "skill/competence",
                    "reuseLevel": "cross-sector",
                    "preferredLabel": " Software testing ",
                    "altLabels": "QA testing",
                    "hiddenLabels": "",
                    "status": "released",
                    "definition": " Tests software. ",
                    "description": "Description fallback.",
                    "scopeNote": "Scope note.",
                    "inScheme": "scheme",
                },
                {
                    "conceptUri": "uri:skill:not-needed",
                    "conceptType": "Skill",
                    "skillType": "knowledge",
                    "reuseLevel": "sector-specific",
                    "preferredLabel": "Not needed",
                    "altLabels": "",
                    "hiddenLabels": "",
                    "status": "released",
                    "definition": "Skipped.",
                    "description": "",
                    "scopeNote": "",
                    "inScheme": "scheme",
                },
                {
                    "conceptUri": "uri:skill:two",
                    "conceptType": "Skill",
                    "skillType": "knowledge",
                    "reuseLevel": "occupation-specific",
                    "preferredLabel": "",
                    "altLabels": "",
                    "hiddenLabels": "",
                    "status": "released",
                    "definition": "Missing label.",
                    "description": "",
                    "scopeNote": "",
                    "inScheme": "scheme",
                },
            ],
            [
                "conceptUri",
                "conceptType",
                "skillType",
                "reuseLevel",
                "preferredLabel",
                "altLabels",
                "hiddenLabels",
                "status",
                "definition",
                "description",
                "scopeNote",
                "inScheme",
            ],
        )

        result = import_esco_skills.parse_skills_csv(
            skills_path,
            {"uri:skill:one", "uri:skill:two", "uri:skill:missing"},
        )

        self.assertEqual(result.stats.total_skills_rows_read, 3)
        self.assertEqual(len(result.skills), 1)
        skill = result.skills[0]
        self.assertEqual(skill.esco_skill_uri, "uri:skill:one")
        self.assertEqual(skill.preferred_label, "Software testing")
        self.assertEqual(skill.description, "Description fallback.")
        self.assertEqual(skill.scope_note, "Scope note.")
        self.assertEqual(
            {missing.esco_skill_uri: missing.reason for missing in result.missing_skills},
            {
                "uri:skill:two": "missing_preferred_label",
                "uri:skill:missing": "not_found_in_skills_csv",
            },
        )
        self.assertEqual(
            [(row.esco_skill_uri, row.included, row.skip_reason) for row in result.review_rows],
            [
                ("uri:skill:one", True, ""),
                ("uri:skill:not-needed", False, "skill_not_linked_to_imported_occupations"),
                ("uri:skill:two", False, "missing_preferred_label"),
            ],
        )

    def test_parse_skills_supports_human_readable_columns(self):
        skills_path = self.write_csv(
            "skills_en.csv",
            [
                {
                    "Concept URI": "uri:skill:one",
                    "Concept type": "KnowledgeSkillCompetence",
                    "skillType": "knowledge",
                    "reuseLevel": "cross-sector",
                    "Concept PT": "Cloud computing",
                    "Definition": "Uses cloud platforms.",
                }
            ],
            [
                "Concept URI",
                "Concept type",
                "skillType",
                "reuseLevel",
                "Concept PT",
                "Definition",
            ],
        )

        result = import_esco_skills.parse_skills_csv(skills_path, {"uri:skill:one"})

        self.assertEqual(len(result.skills), 1)
        self.assertEqual(result.skills[0].preferred_label, "Cloud computing")

    def test_write_review_outputs(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        base_path = Path(directory.name)

        import_esco_skills.write_skills_review_csv(
            base_path / "skills.csv",
            [
                import_esco_skills.SkillReviewRow(
                    esco_skill_uri="uri:skill",
                    preferred_label="Testing",
                    skill_type="skill/competence",
                    reuse_level="cross-sector",
                    included=True,
                    skip_reason="",
                )
            ],
        )
        import_esco_skills.write_missing_skills_csv(
            base_path / "missing.csv",
            [
                import_esco_skills.MissingSkillRow(
                    esco_skill_uri="uri:missing",
                    relation_count=2,
                    reason="not_found_in_skills_csv",
                )
            ],
        )
        import_esco_skills.write_relations_review_csv(
            base_path / "relations.csv",
            [
                import_esco_skills.RelationReviewRow(
                    esco_uri="uri:occupation",
                    esco_skill_uri="uri:skill",
                    relation_type="essential",
                    included=True,
                    skip_reason="",
                )
            ],
        )

        with (base_path / "skills.csv").open(newline="", encoding="utf-8") as handle:
            self.assertEqual(
                list(csv.DictReader(handle)),
                [
                    {
                        "esco_skill_uri": "uri:skill",
                        "preferred_label": "Testing",
                        "skill_type": "skill/competence",
                        "reuse_level": "cross-sector",
                        "included": "true",
                        "skip_reason": "",
                    }
                ],
            )
        with (base_path / "missing.csv").open(newline="", encoding="utf-8") as handle:
            self.assertEqual(
                list(csv.DictReader(handle)),
                [
                    {
                        "esco_skill_uri": "uri:missing",
                        "relation_count": "2",
                        "reason": "not_found_in_skills_csv",
                    }
                ],
            )
        with (base_path / "relations.csv").open(newline="", encoding="utf-8") as handle:
            self.assertEqual(
                list(csv.DictReader(handle)),
                [
                    {
                        "esco_uri": "uri:occupation",
                        "esco_skill_uri": "uri:skill",
                        "relation_type": "essential",
                        "included": "true",
                        "skip_reason": "",
                    }
                ],
            )

    def test_import_reuses_existing_rows_by_default_and_updates_with_force(self):
        skill = import_esco_skills.EscoSkill(
            esco_skill_uri="uri:skill:existing",
            skill_type="knowledge",
            reuse_level="cross-sector",
            preferred_label="Cloud computing",
            alt_labels="Cloud",
            hidden_labels=None,
            description=None,
            scope_note=None,
        )
        relation = import_esco_skills.EscoOccupationSkill(
            esco_uri="uri:occupation",
            esco_skill_uri="uri:skill:existing",
            relation_type="essential",
            skill_type="knowledge",
        )
        client = FakeClient({"uri:occupation"})
        client.skills["uri:skill:existing"] = {
            "esco_skill_uri": "uri:skill:existing",
            "preferred_label": "Old label",
        }
        client.relations[relation.identity_key()] = relation.to_payload()

        default_stats = import_esco_skills.import_esco_skills(
            [skill],
            [relation],
            client,
        )
        force_stats = import_esco_skills.import_esco_skills(
            [skill],
            [relation],
            client,
            force=True,
        )

        self.assertEqual(default_stats.skills_reused, 1)
        self.assertEqual(default_stats.relations_reused, 1)
        self.assertEqual(default_stats.skills_updated, 0)
        self.assertEqual(default_stats.relations_updated, 0)
        self.assertEqual(force_stats.skills_updated, 1)
        self.assertEqual(force_stats.relations_updated, 1)
        self.assertEqual(client.updated_skills[0]["preferred_label"], "Cloud computing")

    def test_import_inserts_missing_rows(self):
        skill = import_esco_skills.EscoSkill(
            esco_skill_uri="uri:skill:new",
            skill_type="skill/competence",
            reuse_level="cross-sector",
            preferred_label="Testing",
            alt_labels=None,
            hidden_labels=None,
            description=None,
            scope_note=None,
        )
        relation = import_esco_skills.EscoOccupationSkill(
            esco_uri="uri:occupation",
            esco_skill_uri="uri:skill:new",
            relation_type="optional",
            skill_type="skill/competence",
        )
        client = FakeClient({"uri:occupation"})

        stats = import_esco_skills.import_esco_skills([skill], [relation], client)

        self.assertEqual(stats.skills_inserted, 1)
        self.assertEqual(stats.relations_inserted, 1)
        self.assertEqual(client.inserted_skills[0]["esco_skill_uri"], "uri:skill:new")
        self.assertEqual(
            set(client.inserted_skills[0]),
            {
                "esco_skill_uri",
                "skill_type",
                "reuse_level",
                "preferred_label",
                "alt_labels",
                "hidden_labels",
                "description",
                "scope_note",
            },
        )
        self.assertEqual(client.inserted_relations[0]["relation_type"], "optional")
        self.assertNotIn("raw_data", client.inserted_relations[0])

    def test_list_existing_skills_uses_small_lookup_chunks(self):
        client = import_esco_skills.SupabaseRestClient(
            "https://example.supabase.co",
            "sb_secret_test",
        )
        requested_filters = []

        def fake_request(method, table, query=None, payload=None, prefer=None, extra_headers=None):
            self.assertEqual(method, "GET")
            self.assertEqual(table, "esco_skills")
            requested_filters.append(dict(query)["esco_skill_uri"])
            return []

        client._request = fake_request

        client.list_existing_skills(
            {
                f"http://data.europa.eu/esco/skill/{index:04d}"
                for index in range(250)
            }
        )

        self.assertEqual(len(requested_filters), 3)
        self.assertTrue(all(value.startswith("in.(") for value in requested_filters))
        self.assertTrue(all(value.count('"http://') <= 100 for value in requested_filters))

    def test_load_dotenv_file_sets_missing_values_without_overwriting_environment(self):
        directory = TemporaryDirectory()
        path = Path(directory.name) / ".env"
        self.addCleanup(directory.cleanup)
        path.write_text(
            "\n".join(
                [
                    "SUPABASE_URL=https://from-file.supabase.co",
                    "SUPABASE_SERVICE_ROLE_KEY='sb_secret_from_file'",
                ]
            ),
            encoding="utf-8",
        )

        previous_url = os.environ.get("SUPABASE_URL")
        previous_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        try:
            os.environ["SUPABASE_URL"] = "https://from-env.supabase.co"
            os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)

            import_esco_skills.load_dotenv_file(path)

            self.assertEqual(os.environ["SUPABASE_URL"], "https://from-env.supabase.co")
            self.assertEqual(os.environ["SUPABASE_SERVICE_ROLE_KEY"], "sb_secret_from_file")
        finally:
            if previous_url is None:
                os.environ.pop("SUPABASE_URL", None)
            else:
                os.environ["SUPABASE_URL"] = previous_url
            if previous_key is None:
                os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
            else:
                os.environ["SUPABASE_SERVICE_ROLE_KEY"] = previous_key


if __name__ == "__main__":
    unittest.main()
