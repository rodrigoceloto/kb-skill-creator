---
name: kb-skill-creator
description: Turn documents into searchable knowledge base skills for Claude Code. Use this whenever the user wants to index a PDF, chunk a document, import docs for Claude to reference, make a file searchable, build a knowledge base from documentation, or organize a large document into browsable sections — even if they don't use the term 'knowledge base'. Supports PDF, Markdown, and text files.
---

# Knowledge Base Skill Creator

Use this skill to turn documents into semantically-structured knowledge bases that Claude Code can browse on demand. It uses **semantic analysis** — chunking by logical boundaries (chapters, articles, subsections) rather than fixed token counts — because retrieval quality depends on each chunk being a coherent, self-contained unit.

## Two-Phase Process

Two phases keep the workflow safe: Phase 1 lets you validate and refine the structure before committing to file generation.

**Phase 1: Semantic Analysis**
```bash
python3 .claude/skills/kb-skill-creator/scripts/generate_kb.py \
  --name "kb-name" \
  --sources "path/to/document.pdf" \
  --description "Description of the knowledge base" \
  --analyze-only
```

After the script creates the analysis workspace:

1. Read `ANALYSIS_REQUEST.md` and source documents from `workspace/samples/`.
2. Identify the document type, language, and major structural divisions (chapters, titles, sections).
3. Recursively identify subdivisions and create semantic boundaries at logical points.
4. Write `structure.json` with the hierarchical structure.
5. Re-run with `--analyze-only` to trigger automatic validation (all leaf sections must be ≤~5000 tokens).
6. If oversized sections are found, read the generated `SUBDIVISION_REQUEST.md`, add `children` to oversized entries in `structure.json`, and repeat from step 5.

**Phase 2: Skill Generation**
```bash
python3 .claude/skills/kb-skill-creator/scripts/generate_kb.py \
  --name "kb-name" \
  --from-structure "path/to/structure.json"
```

Generates the final skill with semantically-organized chunks.

## Parameters

- `--name`: Knowledge base skill name (lowercase, hyphens only, max 64 chars)
- `--sources`: One or more source document paths (PDF, MD, TXT)
- `--description`: What this knowledge base contains (max 1024 chars). Write this carefully — Claude uses it to decide when to consult the KB.
- `--analyze-only`: Phase 1 — perform semantic analysis only
- `--from-structure`: Phase 2 — generate from existing structure.json
- `--max-tokens`: Target tokens per chunk (default: 5000). Lower values yield more precise retrieval; higher values preserve more surrounding context. Adjust based on document density.

## Generated Structure

```
kb-name/
├── SKILL.md              # Main skill file (auto-discoverable)
├── index.md              # Hierarchical table of contents
├── structure.json        # Complete semantic analysis
├── metadata.json         # Chunk metadata
└── chunks/               # Semantic sections
    ├── section_001.md
    ├── section_002.md
    ├── section_002_001.md
    └── ...
```

Each chunk is a semantically complete section with a hierarchical breadcrumb path, semantic type tag, actual token count, and full content.

## Example

```bash
# Phase 1: Analyze a product manual
python3 .claude/skills/kb-skill-creator/scripts/generate_kb.py \
  --name "router-manual" \
  --sources "files/router-user-guide.pdf" \
  --description "User guide for XR-500 router: setup, configuration, troubleshooting" \
  --analyze-only

# → Read ANALYSIS_REQUEST.md, analyze the document, write structure.json
# → Re-run with --analyze-only to validate; subdivide oversized sections as needed

# Phase 2: Generate the skill
python3 .claude/skills/kb-skill-creator/scripts/generate_kb.py \
  --name "router-manual" \
  --from-structure ".claude/skills/router-manual_analysis/structure.json"
```

## Analysis Guidelines

When performing semantic analysis, follow these practices:

1. **Sample first**: Read the beginning, middle, and end of the document to understand its type and structure before committing to a full read. This avoids reading massive files in their entirety.
2. **Find top-level markers with Grep**: Use the `-n` flag to get line numbers.
   ```
   Grep(pattern="^Chapter \\d+", output_mode="content", -n=True)
   ```
3. **Use line numbers for boundaries**: Store `start_line` and `end_line` (0-indexed) in structure.json. Line numbers are the only method used for extraction — they eliminate the ambiguity that text markers can have when the same heading appears multiple times. Include `start_marker` for human readability only.
4. **Let the system estimate tokens**: Do not calculate `estimated_tokens` manually. The system computes it automatically from document density (`(end_line - start_line) × tokens_per_line`). Provide only `start_line` and `end_line`.
5. **Subdivide recursively until all leaves fit**: Keep subdividing until every leaf section is ≤~5000 tokens. Do not stop at first-level subdivision if sections are still oversized. The ~5000 target balances retrieval precision against losing cross-reference context within a section.
6. **Respect semantic boundaries**: Split at meaning boundaries (articles, subsections, procedures). Stop dividing when a section is a complete logical unit that cannot be split without losing coherence. Document truly atomic sections in `analyzer_notes`.
7. **Validate before generating**: Ensure no gaps or overlaps in line ranges across the full structure.

## Error Handling

- **PDF extraction fails** (image-based PDF or missing `pypdf`): Install `pypdf` (`pip install pypdf>=3.0.0`). For scanned/image-based PDFs, OCR the file first — `pypdf` cannot extract text from images.
- **No detectable structure**: If the document lacks headings or clear divisions, fall back to paragraph-based chunking using blank-line boundaries.
- **Oversized sections persist after subdivision**: If a section cannot be split further semantically, either increase `--max-tokens` to accommodate it or accept the oversized chunk and note it in `analyzer_notes`.
- **Overlapping or gapped line ranges**: Run `python3 .claude/skills/kb-skill-creator/scripts/validate_structure.py path/to/structure.json` to detect and diagnose range issues.
