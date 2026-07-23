# Third-party notices

The Career Compass MIT license covers project-authored code only. Data, models, and bundled third-party assets remain under their own terms.

## MIND tech-skills ontology

Career Compass includes a compressed copy of `__aggregated_skills.json` from the [MIND tech-skills ontology](https://github.com/MIND-TechAI/MIND-tech-ontology), pinned to commit [`2367527d1a2f5665f595d6e0518294cc69dfb0fe`](https://github.com/MIND-TechAI/MIND-tech-ontology/tree/2367527d1a2f5665f595d6e0518294cc69dfb0fe).

- Bundled file: `backend/data/__aggregated_skills.json.gz`
- SHA-256 of the uncompressed upstream JSON: `5ba9aedda04a5052a6b8cdec796ab4350d507a2696986259541950351f4b2e14`
- Upstream license: MIT

```text
MIT License

Copyright (c) 2025 or-mihai-or-gheorghe

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## ESCO

This service uses the ESCO classification of the European Commission.

Career Compass uses a filtered subset of ESCO occupation, skill, and occupation-skill records and adds project-specific mappings. It is not an unmodified ESCO distribution. ESCO reuse is governed by [Commission Decision 2011/833/EU and the ESCO reuse conditions](https://esco.ec.europa.eu/en/about-esco/faq?page=1).

## IT Job Roles Skills Dataset

The hosted role catalog began with the [IT Job Roles Skills Dataset by Dhivya Dharuna B A](https://www.kaggle.com/datasets/dhivyadharunaba/it-job-roles-skills-dataset), which publishes database content under its listed Open Database/original-author terms. Career Compass adds deterministic normalization, domain tags, embeddings, ESCO mappings, and reviewed salary metadata.

## German occupational and salary statistics

Salary bands derive from the Bundesagentur für Arbeit's ["Entgelte nach Berufen im Vergleich"](https://statistik.arbeitsagentur.de/DE/Navigation/Statistiken/Interaktive-Statistiken/Entgelte-Berufe/Entgelte-nach-Berufen-im-Vergleich-Nav.html) and KldB occupational groups. Values are project-derived estimates at occupational-group and requirement-level granularity, not exact salaries for individual job titles.

## BGE embedding model

The backend downloads and uses [`BAAI/bge-base-en-v1.5`](https://huggingface.co/BAAI/bge-base-en-v1.5) for local text embeddings. The model is published under the MIT license; its weights are not committed to this repository.

## pypdf

The backend uses [`pypdf`](https://github.com/py-pdf/pypdf) for in-memory PDF text extraction. pypdf is distributed under the [BSD 3-Clause license](https://github.com/py-pdf/pypdf/blob/main/LICENSE).
