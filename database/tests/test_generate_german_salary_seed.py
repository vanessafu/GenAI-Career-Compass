import csv
import importlib.util
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "generate_german_salary_seed.py"
)
spec = importlib.util.spec_from_file_location("generate_german_salary_seed", SCRIPT_PATH)
generate_german_salary_seed = importlib.util.module_from_spec(spec)
sys.modules["generate_german_salary_seed"] = generate_german_salary_seed
spec.loader.exec_module(generate_german_salary_seed)


def write_minimal_xlsx(path, rows):
    shared_strings = []
    shared_string_indexes = {}

    def shared_index(value):
        text = "" if value is None else str(value)
        if text not in shared_string_indexes:
            shared_string_indexes[text] = len(shared_strings)
            shared_strings.append(text)
        return shared_string_indexes[text]

    sheet_rows = []
    for row_number, row in enumerate(rows, start=1):
        cells = []
        for col_number, value in enumerate(row, start=1):
            col_name = ""
            number = col_number
            while number:
                number, remainder = divmod(number - 1, 26)
                col_name = chr(65 + remainder) + col_name
            cell_ref = f"{col_name}{row_number}"
            index = shared_index(value)
            cells.append(f'<c r="{cell_ref}" t="s"><v>{index}</v></c>')
        sheet_rows.append(f'<row r="{row_number}">{"".join(cells)}</row>')

    shared_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'count="{len(shared_strings)}" uniqueCount="{len(shared_strings)}">'
        + "".join(f"<si><t>{escape(value)}</t></si>" for value in shared_strings)
        + "</sst>"
    )
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows)}</sheetData>'
        "</worksheet>"
    )

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/sharedStrings.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
            "</Types>",
        )
        archive.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Tabelle1" sheetId="1" r:id="rId1"/></sheets>'
            "</workbook>",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet1.xml"/>'
            "</Relationships>",
        )
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        archive.writestr("xl/sharedStrings.xml", shared_xml)


class GenerateGermanSalarySeedTests(unittest.TestCase):
    def test_kldb_lookup_attempts_derive_level_and_group_fallbacks(self):
        attempts = generate_german_salary_seed.kldb_lookup_attempts("43412")

        self.assertEqual(
            attempts,
            [
                generate_german_salary_seed.KldbLookupAttempt(
                    code="43412",
                    level="Fachkraft",
                    broad_fallback=False,
                ),
                generate_german_salary_seed.KldbLookupAttempt(
                    code="4341",
                    level="Fachkraft",
                    broad_fallback=True,
                ),
                generate_german_salary_seed.KldbLookupAttempt(
                    code="434",
                    level="Fachkraft",
                    broad_fallback=True,
                ),
            ],
        )

    def test_parse_salary_payload_preserves_capped_display_value(self):
        payload = {
            "beruf": "Softwareentwickler/in",
            "entgeltMedian": ">7.450 Euro",
            "unteresQuartil": "5.500",
            "oberesQuartil": ">7.450",
            "datenstand": "Entgeltatlas 2024",
        }

        salary = generate_german_salary_seed.parse_salary_payload(
            payload,
            fallback_title="Softwareentwickler/in",
            lookup_code_used="43412",
            lookup_level_used="Fachkraft",
            fallback_group_used=False,
        )

        self.assertEqual(salary.median_monthly_gross_eur, 7450)
        self.assertEqual(salary.median_display, ">7.450 Euro")
        self.assertEqual(salary.low_monthly_gross_eur, 5500)
        self.assertEqual(salary.high_monthly_gross_eur, 7450)
        self.assertTrue(salary.salary_value_capped)
        self.assertEqual(salary.lookup_code_used, "43412")
        self.assertEqual(salary.lookup_level_used, "Fachkraft")

    def test_salary_table_parser_extracts_ba_group_rows(self):
        html = """
        <table>
          <tr><th>Berufsgruppe</th><th>Insgesamt</th><th>Helfer</th><th>Fachkräfte</th><th>Spezialisten</th><th>Experten</th></tr>
          <tr><td>431 Informatik</td><td>5704.70</td><td>-</td><td>4959.64</td><td>6267.43</td><td>6457.25</td></tr>
          <tr><td>433 IT-Netzwerkt.,-Koord.,-Administr.,-Orga.</td><td>5818.63</td><td>-</td><td>x</td><td>5589.73</td><td>7312.93</td></tr>
          <tr><td>434 Softwareentwicklung und Programmierung</td><td>6022.53</td><td>-</td><td>4449.05</td><td>6081.96</td><td>6143.95</td></tr>
        </table>
        """

        rows = generate_german_salary_seed.parse_salary_table_html(html)

        self.assertEqual(rows["431"].group_title, "Informatik")
        self.assertEqual(rows["431"].cells["fachkraefte"].value, 4960)
        self.assertEqual(rows["433"].cells["fachkraefte"].value, None)
        self.assertEqual(rows["433"].cells["experten"].value, 7313)

    def test_salary_table_lookup_uses_level_column_and_records_table_fields(self):
        table_rows = generate_german_salary_seed.parse_salary_table_html(
            """
            <table>
              <tr><th>Berufsgruppe</th><th>Insgesamt</th><th>Helfer</th><th>Fachkräfte</th><th>Spezialisten</th><th>Experten</th></tr>
              <tr><td>434 Softwareentwicklung und Programmierung</td><td>6022.53</td><td>-</td><td>4449.05</td><td>6081.96</td><td>6143.95</td></tr>
            </table>
            """
        )
        lookup = generate_german_salary_seed.SalaryTableLookup(
            table_rows=table_rows,
            source_label="test table",
        )
        candidate = generate_german_salary_seed.KldbCandidate(
            title="Softwareentwickler/in",
            kldb_code="43412",
            score=100,
            matched_term="Softwareentwickler/in",
            term_source="original_title",
            title_similarity=100,
            original_title_similarity=100,
            it_related=True,
        )

        result = lookup.lookup(candidate)

        self.assertEqual(result.source_status, "salary_table_success")
        self.assertEqual(result.data.median_monthly_gross_eur, 4449)
        self.assertEqual(result.data.median_display, "4449.05")
        self.assertEqual(result.data.salary_group_code, "434")
        self.assertEqual(
            result.data.salary_source_group_title,
            "Softwareentwicklung und Programmierung",
        )
        self.assertEqual(result.data.salary_selected_column, "Fachkräfte")
        self.assertEqual(result.data.salary_fachkraefte_monthly_gross_eur, 4449)

    def test_salary_table_lookup_falls_back_to_ingesamt_and_needs_review(self):
        table_rows = generate_german_salary_seed.parse_salary_table_html(
            """
            <table>
              <tr><th>Berufsgruppe</th><th>Insgesamt</th><th>Helfer</th><th>Fachkräfte</th><th>Spezialisten</th><th>Experten</th></tr>
              <tr><td>433 IT-Netzwerkt.,-Koord.,-Administr.,-Orga.</td><td>5818.63</td><td>-</td><td>x</td><td>5589.73</td><td>7312.93</td></tr>
            </table>
            """
        )
        role = generate_german_salary_seed.CareerRole(
            role_id="33",
            job_title="Network Administrator",
            domain_tags="networking",
            esco_title="network administrator",
            esco_uri="uri:network",
        )
        kldb_rows = [
            generate_german_salary_seed.KldbOccupation(
                title="Netzwerkadministrator/in",
                kldb_code="43312",
            )
        ]

        result = generate_german_salary_seed.build_salary_seed_rows(
            roles=[role],
            kldb_rows=kldb_rows,
            salary_lookup=generate_german_salary_seed.SalaryTableLookup(
                table_rows=table_rows,
                source_label="test table",
            ),
            manual_overrides=[],
            top_k=5,
        )

        seed_row = result.seed_rows[0]
        self.assertEqual(seed_row["salary_median_monthly_gross_eur"], "5819")
        self.assertEqual(seed_row["salary_selected_column"], "Insgesamt")
        self.assertEqual(seed_row["salary_group_code"], "433")
        self.assertEqual(seed_row["source_status"], "salary_table_success")
        self.assertEqual(seed_row["needs_review"], "true")

    def test_salary_band_rules_include_unknown_and_capped_values(self):
        self.assertEqual(
            generate_german_salary_seed.salary_band_and_score(None, False),
            ("unknown", 0),
        )
        self.assertEqual(
            generate_german_salary_seed.salary_band_and_score(3999, False),
            ("low", 1),
        )
        self.assertEqual(
            generate_german_salary_seed.salary_band_and_score(4000, False),
            ("medium", 2),
        )
        self.assertEqual(
            generate_german_salary_seed.salary_band_and_score(5500, False),
            ("high", 3),
        )
        self.assertEqual(
            generate_german_salary_seed.salary_band_and_score(7000, False),
            ("very_high", 4),
        )
        self.assertEqual(
            generate_german_salary_seed.salary_band_and_score(7450, True),
            ("capped", 5),
        )

    def test_search_terms_include_title_esco_and_domain_fallbacks(self):
        role = generate_german_salary_seed.CareerRole(
            role_id="7",
            job_title="MLOps Engineer",
            domain_tags="ai_ml,cloud",
            esco_title="Software developer",
            esco_uri="uri:esco",
        )

        terms = generate_german_salary_seed.generate_search_terms(role)

        self.assertEqual(terms[0].term, "MLOps Engineer")
        self.assertIn("Software developer", [term.term for term in terms])
        self.assertIn("Data Scientist", [term.term for term in terms])
        self.assertIn("Cloud Engineer", [term.term for term in terms])
        self.assertIn("Softwareentwickler/in", [term.term for term in terms])

    def test_kldb_xlsx_loader_detects_title_and_code_columns(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workbook_path = Path(tmpdir) / "kldb.xlsx"
            write_minimal_xlsx(
                workbook_path,
                [
                    ["Berufsbenennung", "KldB-Schluessel", "Notizen"],
                    ["Softwareentwickler/in", "43412", ""],
                    ["IT-Systemadministrator/in", "43343", ""],
                ],
            )

            rows = generate_german_salary_seed.load_kldb_workbook(workbook_path)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].title, "Softwareentwickler/in")
        self.assertEqual(rows[0].kldb_code, "43412")

    def test_exact_kldb_match_can_be_selected_but_still_needs_review_without_salary(self):
        role = generate_german_salary_seed.CareerRole(
            role_id="12",
            job_title="Softwareentwickler/in",
            domain_tags="software_engineering",
            esco_title="Software developer",
            esco_uri="uri:software",
        )
        kldb_rows = [
            generate_german_salary_seed.KldbOccupation(
                title="Softwareentwickler/in",
                kldb_code="43412",
            )
        ]

        result = generate_german_salary_seed.build_salary_seed_rows(
            roles=[role],
            kldb_rows=kldb_rows,
            salary_lookup=generate_german_salary_seed.NoApiSalaryLookup(),
            manual_overrides=[],
            top_k=5,
        )

        seed_row = result.seed_rows[0]
        review_row = result.review_rows[0]
        self.assertEqual(seed_row["entgeltatlas_match_title"], "Softwareentwickler/in")
        self.assertEqual(seed_row["kldb_code"], "43412")
        self.assertEqual(seed_row["salary_band"], "unknown")
        self.assertEqual(seed_row["salary_score"], "0")
        self.assertEqual(seed_row["match_confidence"], "exact_title")
        self.assertEqual(seed_row["source_status"], "no_api_configured")
        self.assertEqual(seed_row["needs_review"], "true")
        self.assertEqual(seed_row["salary_lookup_code_used"], "")
        self.assertEqual(seed_row["salary_lookup_level_used"], "")
        self.assertEqual(review_row["selected_match_title"], "Softwareentwickler/in")

    def test_fallback_salary_lookup_fills_code_level_and_needs_review(self):
        class FakeFallbackLookup:
            default_status = "api_missing"
            api_configured = True
            request_count = 0

            def lookup(self, candidate):
                self.request_count += 1
                return generate_german_salary_seed.SalaryLookupResult(
                    data=generate_german_salary_seed.SalaryData(
                        median_monthly_gross_eur=6200,
                        median_display="6200",
                        low_monthly_gross_eur=5100,
                        high_monthly_gross_eur=7200,
                        match_title=candidate.title,
                        region="Deutschland",
                        data_period="Entgeltatlas 2024",
                        lookup_code_used="4341",
                        lookup_level_used="Fachkraft",
                        fallback_group_used=True,
                    ),
                    source_status="fallback_group_used",
                    notes="Fallback code 4341 returned salary data.",
                )

        role = generate_german_salary_seed.CareerRole(
            role_id="12",
            job_title="Softwareentwickler/in",
            domain_tags="software_engineering",
            esco_title="Software developer",
            esco_uri="uri:software",
        )
        kldb_rows = [
            generate_german_salary_seed.KldbOccupation(
                title="Softwareentwickler/in",
                kldb_code="43412",
            )
        ]

        result = generate_german_salary_seed.build_salary_seed_rows(
            roles=[role],
            kldb_rows=kldb_rows,
            salary_lookup=FakeFallbackLookup(),
            manual_overrides=[],
            top_k=5,
        )

        seed_row = result.seed_rows[0]
        self.assertEqual(seed_row["salary_median_monthly_gross_eur"], "6200")
        self.assertEqual(seed_row["salary_band"], "high")
        self.assertEqual(seed_row["salary_score"], "3")
        self.assertEqual(seed_row["salary_lookup_code_used"], "4341")
        self.assertEqual(seed_row["salary_lookup_level_used"], "Fachkraft")
        self.assertEqual(seed_row["source_status"], "fallback_group_used")
        self.assertEqual(seed_row["needs_review"], "true")

    def test_entgeltatlas_lookup_tries_full_code_then_fallback_until_data(self):
        class FakeEntgeltatlasLookup(generate_german_salary_seed.EntgeltatlasApiSalaryLookup):
            def __init__(self):
                super().__init__(
                    base_url="https://example.test/pc/v1",
                    x_api_key="test-token",
                    client_id="",
                    client_secret="",
                    cache_dir=Path("unused"),
                    min_request_interval_seconds=0,
                )
                self.urls = []

            def _load_or_request(self, url):
                self.urls.append(url)
                if "/entgelte/43412?" in url:
                    return {
                        "status_code": 200,
                        "response_text": "{}",
                    }
                if "/entgelte/4341?" in url:
                    return {
                        "status_code": 200,
                        "response_text": (
                            '{"beruf":"Softwareentwickler/in",'
                            '"entgeltMedian":"6200"}'
                        ),
                    }
                self.fail(f"Unexpected lookup URL: {url}")

        candidate = generate_german_salary_seed.KldbCandidate(
            title="Softwareentwickler/in",
            kldb_code="43412",
            score=100,
            matched_term="Softwareentwickler/in",
            term_source="original_title",
            title_similarity=100,
            original_title_similarity=100,
            it_related=True,
        )

        lookup = FakeEntgeltatlasLookup()
        result = lookup.lookup(candidate)

        self.assertEqual(len(lookup.urls), 2)
        self.assertIn("/entgelte/43412?", lookup.urls[0])
        self.assertIn("/entgelte/4341?", lookup.urls[1])
        self.assertEqual(result.source_status, "fallback_group_used")
        self.assertEqual(result.data.lookup_code_used, "4341")
        self.assertEqual(result.data.lookup_level_used, "Fachkraft")

    def test_entgeltatlas_optional_config_is_loaded_from_dotenv_only(self):
        previous_values = {
            name: os.environ.get(name)
            for name in [
                "ENTGELTATLAS_BASE_URL",
                "ENTGELTATLAS_X_API_KEY",
                "ENTGELTATLAS_CLIENT_ID",
                "ENTGELTATLAS_CLIENT_SECRET",
            ]
        }
        previous_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.chdir(tmpdir)
                os.environ["ENTGELTATLAS_BASE_URL"] = "https://env-only.example"
                os.environ["ENTGELTATLAS_X_API_KEY"] = "env-token"

                lookup = generate_german_salary_seed.build_salary_lookup(
                    no_api=False,
                    cache_dir=Path("cache"),
                )

                self.assertIsInstance(lookup, generate_german_salary_seed.NoApiSalaryLookup)

                Path(".env").write_text(
                    "ENTGELTATLAS_BASE_URL=https://dotenv.example/pc/v1\n"
                    "ENTGELTATLAS_X_API_KEY=dotenv-token\n",
                    encoding="utf-8",
                )
                lookup = generate_german_salary_seed.build_salary_lookup(
                    no_api=False,
                    cache_dir=Path("cache"),
                )

                self.assertIsInstance(
                    lookup,
                    generate_german_salary_seed.EntgeltatlasApiSalaryLookup,
                )
                self.assertEqual(lookup.base_url, "https://dotenv.example/pc/v1")
            finally:
                os.chdir(previous_cwd)
                for name, value in previous_values.items():
                    if value is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = value

    def test_capped_salary_lookup_sets_capped_status_band_and_review(self):
        class FakeCappedLookup:
            default_status = "api_missing"
            api_configured = True
            request_count = 0

            def lookup(self, candidate):
                self.request_count += 1
                return generate_german_salary_seed.SalaryLookupResult(
                    data=generate_german_salary_seed.SalaryData(
                        median_monthly_gross_eur=7450,
                        median_display=">7.450 Euro",
                        salary_value_capped=True,
                        match_title=candidate.title,
                        region="Deutschland",
                        data_period="Entgeltatlas 2024",
                        lookup_code_used="43412",
                        lookup_level_used="Fachkraft",
                    ),
                    source_status="salary_capped",
                    notes="Capped Entgeltatlas display value.",
                )

        role = generate_german_salary_seed.CareerRole(
            role_id="12",
            job_title="Softwareentwickler/in",
            domain_tags="software_engineering",
            esco_title="Software developer",
            esco_uri="uri:software",
        )
        kldb_rows = [
            generate_german_salary_seed.KldbOccupation(
                title="Softwareentwickler/in",
                kldb_code="43412",
            )
        ]

        result = generate_german_salary_seed.build_salary_seed_rows(
            roles=[role],
            kldb_rows=kldb_rows,
            salary_lookup=FakeCappedLookup(),
            manual_overrides=[],
            top_k=5,
        )

        seed_row = result.seed_rows[0]
        self.assertEqual(seed_row["salary_median_monthly_gross_eur"], "7450")
        self.assertEqual(seed_row["salary_median_display"], ">7.450 Euro")
        self.assertEqual(seed_row["salary_value_capped"], "true")
        self.assertEqual(seed_row["salary_band"], "capped")
        self.assertEqual(seed_row["salary_score"], "5")
        self.assertEqual(seed_row["source_status"], "api_success")
        self.assertEqual(seed_row["needs_review"], "true")

    def test_manual_override_precedence_and_output_values(self):
        role = generate_german_salary_seed.CareerRole(
            role_id="42",
            job_title="Cloud Security Specialist",
            domain_tags="cloud,cybersecurity",
            esco_title="ICT security manager",
            esco_uri="uri:security",
        )
        override = generate_german_salary_seed.ManualSalaryOverride(
            role_id="42",
            job_title="",
            kldb_code="43344",
            entgeltatlas_match_title="IT-Sicherheitsberater/in",
            salary_median_monthly_gross_eur=7450,
            salary_median_display="> 7450",
            salary_low_monthly_gross_eur=6200,
            salary_high_monthly_gross_eur=None,
            salary_value_capped=True,
            salary_band="capped",
            salary_score=5,
            match_confidence="exact_title",
            notes="Instructor approved.",
        )

        result = generate_german_salary_seed.build_salary_seed_rows(
            roles=[role],
            kldb_rows=[],
            salary_lookup=generate_german_salary_seed.NoApiSalaryLookup(),
            manual_overrides=[override],
            top_k=5,
        )

        seed_row = result.seed_rows[0]
        self.assertEqual(seed_row["source"], "manual_override")
        self.assertEqual(seed_row["entgeltatlas_match_title"], "IT-Sicherheitsberater/in")
        self.assertEqual(seed_row["salary_median_monthly_gross_eur"], "7450")
        self.assertEqual(seed_row["salary_median_display"], "> 7450")
        self.assertEqual(seed_row["salary_band"], "capped")
        self.assertEqual(seed_row["salary_score"], "5")
        self.assertEqual(seed_row["salary_value_capped"], "true")
        self.assertEqual(seed_row["needs_review"], "true")
        self.assertEqual(seed_row["salary_lookup_code_used"], "43344")
        self.assertEqual(seed_row["salary_lookup_level_used"], "Experte")

    def test_write_seed_csv_uses_expected_column_order(self):
        row = {field: "" for field in generate_german_salary_seed.SEED_FIELDNAMES}
        row["role_id"] = "1"
        row["job_title"] = "Software Developer"

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "seed.csv"
            generate_german_salary_seed.write_csv(
                path,
                [row],
                generate_german_salary_seed.SEED_FIELDNAMES,
            )
            with path.open(newline="", encoding="utf-8") as handle:
                reader = csv.reader(handle)
                header = next(reader)

        self.assertEqual(header, generate_german_salary_seed.SEED_FIELDNAMES)


if __name__ == "__main__":
    unittest.main()
