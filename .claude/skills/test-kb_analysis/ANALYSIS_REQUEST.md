# Knowledge Base Structure Analysis Request

## Task

You (Claude Code) are requested to analyze the source document(s) and create a semantic, hierarchical structure for this knowledge base.

## Knowledge Base Information

- **Name**: test-kb
- **Description**: Test knowledge base
- **Target chunk size**: ~5000 tokens (flexible for semantic completeness)

## Source Documents


### sample-doc-1.md

- **Type**: markdown
- **Size**: 393 tokens
- **Location**: `.claude/skills/test-kb_analysis/samples/sample-doc-1.txt`



## Your Task: Progressive Refinement Analysis

Please perform a **progressive refinement analysis** to identify the logical, hierarchical structure of these documents.

### Step 1: Document Type & Top-Level Structure

1. Read samples from the document(s) to understand:
   - What type of document is this? (legal, technical manual, academic, guide, reference, etc.)
   - What language?
   - What are the TOP-LEVEL structural divisions?

For example:
- Legal document: TÍTULO/Title, CAPÍTULO/Chapter, SEÇÃO/Section, Artigo/Article
- Technical manual: Part, Chapter, Section, Procedure
- Academic paper: Abstract, Introduction, Methods, Results, Discussion
- API docs: Overview, Authentication, Endpoints, Error Handling

### Step 2: Identify Major Sections

Scan the complete document(s) and identify all MAJOR SECTIONS (top level of hierarchy).

For each major section, note:
- Title/heading
- Approximate start position or marker text
- Approximate token count
- Whether it needs subdivision (>5000 tokens)

### Step 3: Recursive Subdivision

For sections that are too large (>~5000 tokens), identify logical subdivisions:
- What are the natural subsections?
- How does the document author organized this content?
- What are the semantic boundaries?

Continue recursively until sections are manageable size OR reach atomic level (can't be meaningfully subdivided).

### Step 4: Create Structure JSON

Output the complete hierarchical structure as JSON in this format:

```json
{
  "document_type": "legal_document",
  "language": "pt-BR",
  "hierarchy": [
    {
      "id": "section_001",
      "title": "PREÂMBULO",
      "level": 0,
      "semantic_type": "preamble",
      "start_marker": "Nós, representantes do povo brasileiro",
      "end_marker": "promulgamos a seguinte Constituição",
      "estimated_tokens": 150,
      "children": []
    },
    {
      "id": "section_002",
      "title": "TÍTULO I – DOS PRINCÍPIOS FUNDAMENTAIS",
      "level": 1,
      "semantic_type": "title",
      "start_marker": "TÍTULO I",
      "end_marker": "Art. 4º",
      "estimated_tokens": 800,
      "children": [
        {
          "id": "section_002_001",
          "title": "Art. 1º",
          "level": 2,
          "semantic_type": "article",
          "start_marker": "Art. 1º A República Federativa",
          "end_marker": "V - o pluralismo político.",
          "estimated_tokens": 120,
          "children": []
        }
      ]
    }
  ],
  "metadata": {
    "total_sections": 156,
    "max_depth": 4,
    "analysis_date": "2025-11-03",
    "analyzer_notes": "Portuguese legal document with 4-level hierarchy: TÍTULO → CAPÍTULO → SEÇÃO → Artigo. Some articles are quite long and split into parts."
  }
}
```

## Important Notes

- **Semantic boundaries**: Split based on MEANING, not just token count
- **Complete thoughts**: Each chunk should be a complete logical unit
- **Preserve hierarchy**: Maintain parent-child relationships as they exist in the document
- **Accurate markers**: Start/end markers must be exact text that can be found in the document
- **Token-optimized**: Aim for ~{max_tokens} tokens but prioritize semantic completeness

## Output

Save your structure analysis to: `{workspace / 'structure.json'}`

When complete, the script will automatically proceed to Phase 2 (skill generation).

---

**Ready? Read the documents and create the structure.json file.**
