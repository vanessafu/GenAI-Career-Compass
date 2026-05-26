# GenAi-Career-Compass

## Backend CLI

Activate the environment:

```powershell
mamba activate genai-cuda
```

Extract text from a PDF:

```powershell
python -m backend.app.cli extract-text test_data/cvs/semjon_eschweiler_04_26.pdf
```

Parse a PDF CV into JSON:

```powershell
python -m backend.app.cli parse-cv test_data/cvs/semjon_eschweiler_04_26.pdf
```

Run the full parse and confirmation flow:

```powershell
python -m backend.app.cli confirm-cv test_data/cvs/semjon_eschweiler_04_26.pdf
```

Confirm an already parsed JSON file:

```powershell
python -m backend.app.cli confirm-json outputs/semjon_eschweiler_04_26_parsed.json
```

Enter profile information manually without a CV:

```powershell
python -m backend.app.cli manual-profile
```

The manual and CV-based flows both collect or confirm current role, education,
work experience, projects, certifications, thesis, skills, languages, interests,
and unmapped information into the same confirmed JSON format.
