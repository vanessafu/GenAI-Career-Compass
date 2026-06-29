# Matching Metrics

Generated: 2026-06-29T20:54:43

## Run Metadata

| Field | Value |
| --- | --- |
| Fixture | `C:\Users\benth\Documents\Coding\CareerCompass\metrics\fixtures\matching_profiles.json` |
| Embedding model | `BAAI/bge-base-en-v1.5` |
| Catalog roles | 486 |

## Headline

| Metric | Value |
| --- | ---: |
| nDCG@9 | 72.4% |
| Precision@3 | 92.6% |
| MRR@9 | 100.0% |
| Bucket accuracy | 63.3% |
| Duplicate titles@9 | 0.44 |
| Unjudged roles@9 | 0.00 |
| Successful runs | 9/9 |

## Profiles

| Profile | nDCG@9 | P@3 | MRR@9 | Bucket acc. | Dups | Unjudged | First relevant role | Buckets |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| frontend_student | 77.8% | 100.0% | 100.0% | 100.0% | 0 | 0 | Entry Level Web Developer | ready 3, next 3, aspirational 3 |
| python_data_student | 85.5% | 100.0% | 100.0% | 83.3% | 2 | 0 | Data Analyst | ready 3, next 3, aspirational 3 |
| it_support_beginner | 79.8% | 100.0% | 100.0% | 33.3% | 0 | 0 | IT Technician | ready 3, next 3, aspirational 3 |
| backend_developer | 39.5% | 100.0% | 100.0% | 33.3% | 0 | 0 | Cloud/Software Architect | ready 0, next 3, aspirational 3 |
| design_frontend | 100.0% | 100.0% | 100.0% | 71.4% | 0 | 0 | Front-End Designer | ready 3, next 3, aspirational 3 |
| cloud_security_analyst | 70.8% | 66.7% | 100.0% | 50.0% | 1 | 0 | Cloud Security Engineer | ready 3, next 3, aspirational 3 |
| qa_automation_engineer | 61.4% | 100.0% | 100.0% | 66.7% | 0 | 0 | Junit Engineer | ready 3, next 3, aspirational 3 |
| product_analytics_pm | 76.2% | 66.7% | 100.0% | 42.9% | 1 | 0 | Product Manager | ready 3, next 3, aspirational 3 |
| ux_researcher | 60.7% | 100.0% | 100.0% | 100.0% | 0 | 0 | UX/UI Designer | ready 3, next 3, aspirational 3 |

## Returned Roles

### frontend_student

| Rank | Role ID | Title | Bucket | Relevance | Expected bucket | Judged |
| ---: | --- | --- | --- | ---: | --- | --- |
| 1 | 90 | Entry Level Web Developer | ready_now | 3 | ready_now | yes |
| 2 | 126 | Junior Web Developer | ready_now | 3 | ready_now | yes |
| 3 | 356 | Front-End Designer | ready_now | 2 | ready_now | yes |
| 4 | 39 | Accessibility Specialist | next_step | 2 | next_step | yes |
| 5 | 195 | Web Developer | next_step | 3 | next_step | yes |
| 6 | 118 | Javascript Developer | next_step | 2 | next_step | yes |
| 7 | 98 | Full Stack Developer | aspirational | 1 | aspirational | yes |
| 8 | 123 | Junior iOS Developer | aspirational | 1 | aspirational | yes |
| 9 | 101 | Game Developer | aspirational | 0 | - | yes |

### python_data_student

| Rank | Role ID | Title | Bucket | Relevance | Expected bucket | Judged |
| ---: | --- | --- | --- | ---: | --- | --- |
| 1 | 72 | Data Analyst | ready_now | 3 | ready_now | yes |
| 2 | 29 | Principle Engineer in Data Analysis | ready_now | 1 | aspirational | yes |
| 3 | 317 | Business Intelligence Analyst | ready_now | 3 | ready_now | yes |
| 4 | 363 | Data Science Specialist | next_step | 2 | next_step | yes |
| 5 | 476 | Data Analyst | next_step | 0 | ready_now | yes, duplicate |
| 6 | 304 | Principle Engineer in Data Analysis | next_step | 0 | aspirational | yes, duplicate |
| 7 | 68 | Computer Systems Analyst | aspirational | 1 | aspirational | yes |
| 8 | 10 | Big Data Engineer | aspirational | 1 | aspirational | yes |
| 9 | 85 | Entry Level Developer | aspirational | 0 | - | yes |

### it_support_beginner

| Rank | Role ID | Title | Bucket | Relevance | Expected bucket | Judged |
| ---: | --- | --- | --- | ---: | --- | --- |
| 1 | 436 | IT Technician | ready_now | 3 | ready_now | yes |
| 2 | 439 | Computer Network Specialist | ready_now | 2 | ready_now | yes |
| 3 | 287 | Network and Systems Administrator | ready_now | 2 | next_step | yes |
| 4 | 402 | Technology Assistant | next_step | 2 | ready_now | yes |
| 5 | 423 | IT Support Specialist | next_step | 3 | ready_now | yes |
| 6 | 383 | Computer Support Specialist | next_step | 3 | ready_now | yes |
| 7 | 83 | Docker Engineer | aspirational | 0 | - | yes |
| 8 | 54 | Chef Inspec Engineer | aspirational | 0 | - | yes |
| 9 | 77 | Datadog Engineer | aspirational | 0 | - | yes |

### backend_developer

| Rank | Role ID | Title | Bucket | Relevance | Expected bucket | Judged |
| ---: | --- | --- | --- | ---: | --- | --- |
| 1 | 391 | Cloud/Software Architect | next_step | 1 | aspirational | yes |
| 2 | 56 | Cloud Architect | next_step | 1 | aspirational | yes |
| 3 | 331 | Java Architect | next_step | 2 | aspirational | yes |
| 4 | 259 | Full Stack Java Developer/Programmer/Engineer | aspirational | 2 | next_step | yes |
| 5 | 89 | Entry Level Software Engineer | aspirational | 1 | aspirational | yes |
| 6 | 85 | Entry Level Developer | aspirational | 1 | aspirational | yes |

### design_frontend

| Rank | Role ID | Title | Bucket | Relevance | Expected bucket | Judged |
| ---: | --- | --- | --- | ---: | --- | --- |
| 1 | 356 | Front-End Designer | ready_now | 3 | ready_now | yes |
| 2 | 257 | Front End Developer | ready_now | 3 | ready_now | yes |
| 3 | 39 | Accessibility Specialist | ready_now | 3 | ready_now | yes |
| 4 | 344 | Web Developer | next_step | 2 | next_step | yes |
| 5 | 346 | Web Designer | next_step | 2 | ready_now | yes |
| 6 | 90 | Entry Level Web Developer | next_step | 2 | ready_now | yes |
| 7 | 121 | Junior Developer | aspirational | 1 | aspirational | yes |
| 8 | 85 | Entry Level Developer | aspirational | 0 | - | yes |
| 9 | 120 | Jr Developer | aspirational | 0 | - | yes |

### cloud_security_analyst

| Rank | Role ID | Title | Bucket | Relevance | Expected bucket | Judged |
| ---: | --- | --- | --- | ---: | --- | --- |
| 1 | 60 | Cloud Security Engineer | ready_now | 3 | ready_now | yes |
| 2 | 226 | Cloud Security Engineer | ready_now | 0 | ready_now | yes, duplicate |
| 3 | 374 | Director of Security | ready_now | 1 | aspirational | yes |
| 4 | 375 | Security Administrator | next_step | 2 | ready_now | yes |
| 5 | 225 | Cloud Network Engineer | next_step | 1 | aspirational | yes |
| 6 | 193 | Vault Engineer | next_step | 2 | next_step | yes |
| 7 | 44 | Application Security Engineer | aspirational | 2 | next_step | yes |
| 8 | 241 | DevOps Architect | aspirational | 1 | aspirational | yes |
| 9 | 396 | Platform Engineer | aspirational | 1 | aspirational | yes |

### qa_automation_engineer

| Rank | Role ID | Title | Bucket | Relevance | Expected bucket | Judged |
| ---: | --- | --- | --- | ---: | --- | --- |
| 1 | 280 | Junit Engineer | ready_now | 2 | ready_now | yes |
| 2 | 158 | QA Engineer | ready_now | 3 | ready_now | yes |
| 3 | 165 | Selenium Engineer | ready_now | 3 | ready_now | yes |
| 4 | 340 | Quality Assurance Manager | next_step | 1 | aspirational | yes |
| 5 | 109 | Groovy Engineer | next_step | 1 | aspirational | yes |
| 6 | 397 | Software Quality Assurance Analyst | next_step | 2 | ready_now | yes |
| 7 | 12 | Build and Release Engineer | aspirational | 1 | aspirational | yes |
| 8 | 34 | Senior Build Engineer | aspirational | 1 | aspirational | yes |
| 9 | 18 | DevOps Engineer | aspirational | 1 | aspirational | yes |

### product_analytics_pm

| Rank | Role ID | Title | Bucket | Relevance | Expected bucket | Judged |
| ---: | --- | --- | --- | ---: | --- | --- |
| 1 | 151 | Product Manager | ready_now | 3 | next_step | yes |
| 2 | 425 | Technical Product Manager | ready_now | 3 | next_step | yes |
| 3 | 484 | Product Manager | ready_now | 0 | next_step | yes, duplicate |
| 4 | 215 | Big Data Specialist | next_step | 1 | aspirational | yes |
| 5 | 428 | Portfolio Manager | next_step | 0 | - | yes |
| 6 | 473 | Business Systems Analyst | next_step | 3 | ready_now | yes |
| 7 | 40 | Agile Project Manager | aspirational | 1 | aspirational | yes |
| 8 | 184 | Technical Account Manager | aspirational | 1 | aspirational | yes |
| 9 | 348 | Web Producer | aspirational | 1 | aspirational | yes |

### ux_researcher

| Rank | Role ID | Title | Bucket | Relevance | Expected bucket | Judged |
| ---: | --- | --- | --- | ---: | --- | --- |
| 1 | 343 | UX/UI Designer | ready_now | 3 | ready_now | yes |
| 2 | 112 | Interaction Designer | ready_now | 3 | ready_now | yes |
| 3 | 192 | UX Designer | ready_now | 3 | ready_now | yes |
| 4 | 387 | Database Analyst | next_step | 0 | - | yes |
| 5 | 397 | Software Quality Assurance Analyst | next_step | 0 | - | yes |
| 6 | 72 | Data Analyst | next_step | 0 | - | yes |
| 7 | 8 | Artificial Intelligence Researcher | aspirational | 0 | - | yes |
| 8 | 441 | Computer and Information Research Manager | aspirational | 0 | - | yes |
| 9 | 280 | Junit Engineer | aspirational | 0 | - | yes |
