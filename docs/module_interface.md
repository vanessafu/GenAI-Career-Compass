# Module Interfaces

This document is the alignment contract for Phase 1. Implementations can change
internally, but inputs and outputs should stay consistent. Please write down the type
of the input and output in the document.

## Shared Contract File

All shared data objects live in:

```text
modules/shared/types.py
```

Please have a look at this file and change them. It just gives the prototype.

## CV Parser

File:

```text
modules/data_processing/cv_parser/cv_parser.py
```

Input:

- e.g.  path? pdf?...

Output:

- e.g. `CVParseResult` or json...?

## JSON Processor

File:

```text
modules/data_processing/json_processor/processor.py
```

Input:

- e.g.

Output:

- e.g.

Notes:

- Validate parsed data.
- Identify missing information that matters for matching.
- Then return questions.

## Prompt Generator

File:

```text
modules/recommendation/prompt_generator/generator.py
```

Input:

- `EnrichedUserProfile`

Output:

- `PromptGeneratorOutput`

Notes:

- The generated prompt must be readable and editable by the user.
- Keep prompt sections separate in `editable_sections`.

## RAG Matcher

File:

```text
modules/recommendation/rag_matcher/matcher.py
```

Input:

- e.g. `PromptGeneratorOutput`

Output:

- `e.g.RAGMatcherOutput`

## Database Extractor

File:

```text
modules/data_processing/database_extractor/extractor.py
```

Input:

- e.g.

Output:

- e.g.

Notes:

- Fetch or normalize role details.
- Produce user-facing descriptions, required skills, and next steps...
