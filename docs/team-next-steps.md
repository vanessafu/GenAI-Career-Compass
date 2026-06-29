# Career Compass: Ideas For Team Follow-Up

We now have a viable end-to-end MVP. The core flow is working: users can enter or upload a profile, review it, get role recommendations, inspect skill gaps, and view career roadmaps.

The ideas below are not blockers for the MVP. They are good next steps for making the product more reliable, polished, and impressive.

## 1. Prompt Engineering And Output Quality

- Improve CV parsing prompts for accuracy and completeness.
- Make generated role descriptions more specific and less generic.
- Improve skill-gap explanations so they are concise, helpful, and grounded in the actual gap report.
- Improve roadmap generation so milestones feel realistic and not repetitive.
- Create a small prompt-evaluation set using the same profiles before and after changes.
- Tune model choices so expensive models are used only where they matter most.

## 2. Role Matching And Scoring

- Calibrate scoring weights for skills, intent, seniority, certifications, and domains.
- Check whether the buckets feel right: Ready Now, Next Step, Aspirational.
- Verify that each bucket returns the intended number of roles.
- Explore better embeddings or additional embedding fields.
- Test separate embeddings for user capability, user intent, role requirements, role descriptions, and career interests.
- Review whether certifications are weighted too heavily.
- Add a lightweight reranking step so top results feel more human-reasonable.

## 3. Data Quality, ESCO, And Role Catalog

- Review duplicate roles and strange role titles.
- Check ESCO mappings for weak or low-quality matches.
- Improve ESCO references in the UI where useful.
- Improve or replace generic database role descriptions.
- Consider adding O*NET or another source later for stronger occupational grounding.
- Review salary coverage and make sure salary displays correctly.
- Add a database readiness check before demos or submission.

## 4. CV Upload Accuracy

- Test all mock CVs and a few consenting real/student CVs.
- Compare extracted skills, experience, education, certifications, and interests against the source CV.
- Track common parsing misses.
- Improve the prompt/schema based on those misses.
- Add regression examples for bad parses.
- Check whether privacy stripping removes the personal fields we claim it removes.

## 5. Manual Entry And Recap Review

- Verify that manual input submits every visible field.
- Check that manual and CV-upload flows produce similar matching quality.
- Improve validation prompts for missing role, skills, seniority, interests, and constraints.
- Confirm that Recap edits affect matching, skill gaps, and roadmaps.
- Polish empty states for interests, certifications, projects, and skills.

## 6. Skill Gap Analysis

- Validate that missing skills are actually missing, not just wording or alias mismatches.
- Improve transferable-skill detection.
- Improve priority and effort labels.
- Review the radar chart axes for usefulness.
- Make gap explanations more actionable.
- Add tests for selected roles with known expected gaps.

## 7. Career Roadmaps

- Review whether generated roadmaps feel realistic.
- Make milestone timelines less vague.
- Ensure every roadmap is grounded in the computed gap report.
- Improve recommended projects so they are concrete and portfolio-friendly.
- Only recommend certifications when they are actually relevant.
- Improve mobile behavior for the horizontal roadmap modal.

## 8. Frontend Bugs And UX Polish

- Test the full flow on laptop and mobile widths.
- Fix modal overflow, scrolling, and text wrapping issues.
- Check loading states and failed API states.
- Check keyboard/focus behavior for modals.
- Improve bucket colors and visual hierarchy.
- Make role cards easier to scan.
- Make the "show skill gap" and "show roadmap" flow obvious.

## 9. Testing And QA

- Run backend tests and frontend build before submission.
- Add browser smoke tests for:
  - CV upload
  - manual entry
  - recap edit
  - role matching
  - show skill gap
  - show roadmap
- Create a manual demo checklist.
- Add screenshots or short clips for the final presentation.
- Test bad inputs: empty profile, no skills, bad PDF, and API/network failure.

## 10. Docs And Submission Readiness

- Make sure `README.md` and `SETUP.md` match the current app.
- Document required environment variables and model settings.
- Document the real backend flow.
- Remove stale mock-data or old endpoint references.
- Add known limitations honestly.
- Make sure important untracked files are committed, especially `docs/mvp.md`.

## Suggested Ownership Split

Here is one possible way to divide the work:

- **Prompt engineering / CV quality:** improve parsing, role summaries, skill-gap explanations, and roadmap wording.
- **Matching / data quality:** tune scoring, review embeddings, inspect ESCO mappings, and improve role catalog quality.
- **Frontend polish:** improve mobile behavior, modals, empty states, loading states, and role-card readability.
- **Testing / docs / demo:** create smoke tests, verify setup docs, prepare the demo checklist, and collect screenshots or clips.

## Team Framing

The MVP works end to end now. The next team goal is to make it more reliable, explainable, and polished.
