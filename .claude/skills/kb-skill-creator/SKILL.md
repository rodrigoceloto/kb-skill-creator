---
name: kb-skill-creator
description: Generate semantically-structured knowledge base skills from documents using Claude Code's analysis. Creates discoverable, hierarchically-organized knowledge bases from PDF, Markdown, and text files. Use this when the user wants to create a knowledge base that preserves logical document structure.
---

# Knowledge Base Generator Skill

This skill creates knowledge bases using **semantic analysis** rather than mechanical chunking. Claude Code (you) analyzes the document structure and creates chunks based on logical boundaries, preserving the document's natural organization.

## Two-Phase Process

### Semantic Analysis Mode

When the user requests a knowledge base, use this two-phase semantic analysis process:

**Phase 1: Semantic Analysis (Iterative)**
```bash
python3 .claude/skills/kb-skill-creator/scripts/generate_kb.py \
  --name "kb-name" \
  --sources "path/to/document.pdf" \
  --description "Description of the knowledge base" \
  --analyze-only
```

This creates an analysis workspace and ANALYSIS_REQUEST.md. You (Claude Code) should then:

1. **Initial Analysis:**
   - Read ANALYSIS_REQUEST.md file
   - Read source documents from workspace/samples/ directory
   - Perform progressive refinement analysis:
     - Identify document type and language
     - Find major structural divisions (TÍTULO, Chapter, Section, etc.)
     - Recursively identify subdivisions
     - Create semantic boundaries at logical points
   - Create structure.json with the hierarchical structure

2. **Automatic Validation:** System checks all leaf sections are ≤~5000 tokens

3. **Iterative Subdivision (if needed):**
   - If oversized sections found, system creates SUBDIVISION_REQUEST.md
   - Read SUBDIVISION_REQUEST.md for details on oversized sections
   - For each oversized section:
     - Extract and analyze section content
     - Identify semantic subdivisions (Incisos, §§, subsections, etc.)
     - Update structure.json by adding `children` to oversized section
   - Re-run with `--analyze-only` to validate subdivisions
   - **Repeat** until all leaf sections are ≤~5000 tokens

**Phase 2: Skill Generation**
```bash
python3 .claude/skills/kb-skill-creator/scripts/generate_kb.py \
  --name "kb-name" \
  --from-structure "path/to/structure.json"
```

This generates the final skill with semantically-organized chunks.

**Note:** Phase 2 also validates and creates subdivision requests if oversized sections are found. You can:
- Proceed with generation (accepts warning, may have oversized chunks)
- Or update structure.json and re-run Phase 2 with refined subdivisions

Both phases support iterative subdivision - use whichever fits your workflow.

## Parameters

- `--name`: Knowledge base skill name (lowercase, hyphens only, max 64 chars)
- `--sources`: One or more source document paths (PDF, MD, TXT)
- `--description`: What this knowledge base contains (max 1024 chars)
- `--analyze-only`: Phase 1 flag - perform semantic analysis only
- `--from-structure`: Phase 2 - generate from existing structure.json
- `--max-tokens`: Target tokens per chunk (default: 5000, flexible for semantics)

## Generated Structure

The skill creates a semantically-organized knowledge base:

```
kb-name/
├── SKILL.md              # Main skill file (auto-discoverable)
├── index.md              # Hierarchical table of contents
├── structure.json        # Complete semantic analysis
├── metadata.json         # Chunk metadata
└── chunks/               # Semantic sections
    ├── section_001.md    # First major section
    ├── section_002.md    # Second major section
    ├── section_002_001.md # Subsection of section_002
    └── ...
```

Each chunk represents a **semantically complete section** with:
- Hierarchical path (breadcrumb)
- Semantic type (chapter, article, procedure, etc.)
- Actual token count
- Complete section content

## Features

All generated knowledge bases provide:
- **Hierarchical structure**: Preserves document's logical organization
- **Semantic boundaries**: Chunks follow meaning, not token counts
- **Context preservation**: Each section knows its place in the hierarchy
- **Type classification**: Sections tagged by semantic purpose
- **Token-optimized**: Aims for ~5000 tokens but prioritizes completeness
- **Iterative subdivision**: Automatic detection and guided subdivision of oversized sections
- **Line number precision**: Uses line ranges for 100% accurate extraction (eliminates marker ambiguity)
- **Automatic token estimation**: Calculates estimated tokens based on document density (no manual counting needed)

## Example Workflow

**Creating an API documentation knowledge base:**

```bash
# Phase 1: Start semantic analysis
python3 .claude/skills/kb-skill-creator/scripts/generate_kb.py \
  --name "payment-api-docs" \
  --sources "payment-api-documentation.pdf" \
  --description "Complete API documentation for payment processing platform" \
  --analyze-only
```

**Initial Analysis (Claude Code):**

1. Read `ANALYSIS_REQUEST.md`
2. Read documentation from samples directory
3. Identify structure:
   - Document type: technical_documentation
   - Language: en
   - Major sections: Introduction, Authentication, Core Concepts, API Reference
   - Subsections: Endpoints grouped by resource (Payments, Customers, Refunds)
4. Create initial `structure.json`

**Automatic validation detects oversized sections** → Creates `SUBDIVISION_REQUEST.md`

**Iterative Subdivision (Claude Code) - Two Options:**

**Option A: Refine in Phase 1**
5. Read `SUBDIVISION_REQUEST.md` (lists oversized sections)
6. For each oversized section (e.g., "API Reference - Payments" with 12,000 tokens):
   - Extract full section content
   - Identify logical subdivisions: Create Payment, List Payments, Get Payment, Update Payment, etc.
   - Group related endpoints semantically
   - Update structure.json with children
7. Re-run to validate: `python3 ... --analyze-only`
8. Repeat if any subdivisions still oversized
9. Final validation: All leaf sections ≤5000 tokens ✓

**Option B: Refine in Phase 2**
5. Proceed to Phase 2, validation detects oversized sections
6. Creates `SUBDIVISION_REQUEST.md` with same guidance
7. Update structure.json with subdivisions
8. Re-run Phase 2: `python3 ... --from-structure structure.json`
9. Iterate until all sections valid

```bash
# Phase 2: Generate the skill
python3 .claude/skills/kb-skill-creator/scripts/generate_kb.py \
  --name "payment-api-docs" \
  --from-structure ".claude/skills/payment-api-docs_analysis/structure.json"
```

**Result:** Semantically-organized knowledge base following the documentation's natural hierarchical structure, with all sections properly sized (≤5000 tokens).

## Progressive Refinement Guidelines

When performing semantic analysis:

1. **Sample first**: Read beginning, middle, end to understand document type
2. **Identify top level**: Find major structural markers using Grep with `-n` flag
   - Example: `Grep(pattern="^Chapter \\d+", output_mode="content", -n=True)`
   - Extract line numbers from output for `start_line` and `end_line`
3. **Use line numbers**: Store section boundaries as line numbers (0-indexed)
   - Line numbers are the ONLY method used for extraction
   - More precise and reliable than text markers (eliminates all ambiguity)
   - Include `start_marker` field for human reference (not used for extraction)
4. **Token estimation is automatic**: You do NOT need to calculate `estimated_tokens`
   - System automatically calculates based on document density (tokens/line)
   - Formula: `estimated_tokens = (end_line - start_line) × tokens_per_line`
   - You only provide `start_line` and `end_line`
5. **Recursive subdivision**: For large sections, find logical subsections
   - ⚠️ Keep subdividing until ALL leaf sections are ≤~5000 tokens
   - Don't stop at first-level subdivision if sections are still oversized
6. **Semantic boundaries**: Split based on meaning and document structure
7. **Atomic sections**: Stop dividing when sections are complete logical units
8. **Validate chunk sizes**:
   - Review all leaf sections against ~5000 token target
   - Subdivide any oversized sections further
   - Document atomic sections that cannot be split (in analyzer_notes)
9. **Final validation**: Ensure no gaps or overlaps in line ranges
