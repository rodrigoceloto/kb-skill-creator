#!/usr/bin/env python3
"""
Knowledge Base Generator
Generates discoverable Claude Code skills from document sources
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import hashlib


def count_tokens(text: str) -> int:
    """
    Estimate token count for text.
    Uses a simple approximation: ~4 characters per token for English text.
    For more accuracy, consider using tiktoken library.
    """
    # Simple estimation: 1 token ≈ 4 characters
    return len(text) // 4


def read_markdown(filepath: str) -> str:
    """Read markdown file content."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def read_text(filepath: str) -> str:
    """Read plain text file content."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def read_pdf(filepath: str) -> str:
    """
    Read PDF file content.
    Requires PyPDF2 or pypdf library.
    """
    try:
        import PyPDF2
    except ImportError:
        try:
            import pypdf as PyPDF2
        except ImportError:
            print("Warning: PDF support requires PyPDF2 or pypdf library.")
            print("Install with: pip install pypdf")
            return f"[PDF content from {filepath} - Install pypdf to extract text]"

    try:
        text_content = []
        with open(filepath, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page_num, page in enumerate(pdf_reader.pages, 1):
                text = page.extract_text()
                if text.strip():
                    text_content.append(f"[Page {page_num}]\n{text}")
        return "\n\n".join(text_content)
    except Exception as e:
        return f"[Error reading PDF {filepath}: {str(e)}]"


def process_document(filepath: str) -> Tuple[str, str]:
    """
    Process a document and return its content and type.
    Returns: (content, file_type)
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Document not found: {filepath}")

    ext = path.suffix.lower()

    if ext == '.pdf':
        return read_pdf(filepath), 'pdf'
    elif ext in ['.md', '.markdown']:
        return read_markdown(filepath), 'markdown'
    elif ext in ['.txt', '.text']:
        return read_text(filepath), 'text'
    else:
        # Try to read as text
        try:
            return read_text(filepath), 'text'
        except UnicodeDecodeError:
            return f"[Binary file {filepath} - not supported]", 'binary'




def generate_chunk_hash(content: str) -> str:
    """Generate a short hash for chunk identification."""
    return hashlib.md5(content.encode()).hexdigest()[:8]


def create_hierarchical_index(skill_dir: Path, structure: Dict, chunks: List[Dict]) -> None:
    """Create hierarchical index.md file"""

    index_content = f"""# Knowledge Base Index

This knowledge base contains {len(chunks)} semantic sections organized hierarchically.

## Document Information

- **Type**: {structure.get('document_type', 'unknown')}
- **Language**: {structure.get('language', 'unknown')}
- **Structure Depth**: {structure.get('metadata', {}).get('max_depth', 'unknown')} levels

## Hierarchical Structure

Navigate through the knowledge base using this semantic structure:

"""

    # Create lookup map for actual token counts
    chunk_tokens = {chunk['id']: chunk['tokens'] for chunk in chunks}

    # Build hierarchical tree
    def render_section(node, depth=0):
        indent = "  " * depth
        title = node['title']
        section_id = node['id']
        has_children = len(node.get('children', [])) > 0

        # If node has children, show as header without link (parent node)
        if has_children:
            result = f"{indent}- **{title}**"
        else:
            # Leaf node - create link to chunk file
            chunk_file = f"{section_id}.md"
            result = f"{indent}- [{title}](chunks/{chunk_file})"

        # Add type and token info
        semantic_type = node.get('semantic_type', 'section')

        # Use actual tokens from chunks for leaf nodes (those with chunk files)
        # Use estimated tokens (with ~) for parent nodes (no chunk files)
        if has_children:
            # Parent node - use estimated tokens with ~ prefix
            estimated = node.get('estimated_tokens', 0)
            result += f" *({semantic_type}, ~{estimated} tokens)*\n"
        else:
            # Leaf node - use actual tokens from extraction
            actual_tokens = chunk_tokens.get(section_id, node.get('estimated_tokens', 0))
            result += f" *({semantic_type}, {actual_tokens} tokens)*\n"

        # Process children
        for child in node.get('children', []):
            result += render_section(child, depth + 1)

        return result

    for section in structure.get('hierarchy', []):
        index_content += render_section(section)

    index_content += "\n## How to Use This Index\n\n"
    index_content += "- **Bold titles** indicate parent sections (no duplication - content in children)\n"
    index_content += "- Clickable links take you to complete semantic leaf sections\n"
    index_content += "- Sections preserve the document's logical structure\n"
    index_content += "- Indentation shows hierarchical relationships\n"
    index_content += "- Token counts help gauge section size\n"

    index_path = skill_dir / 'index.md'
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_content)

    print(f"  Index created: {index_path}")


def create_semantic_skill_file(skill_dir: Path, name: str, structure: Dict, chunks: List[Dict]) -> None:
    """Create main SKILL.md file for semantically-chunked knowledge base"""

    skill_content = f"""---
name: {name}
description: {structure.get('metadata', {}).get('analyzer_notes', 'Semantically structured knowledge base')[:1024]}
---

# {name.replace('-', ' ').title()}

This knowledge base was created using **semantic analysis** to preserve the document's logical structure.

## Overview

- **Document Type**: {structure.get('document_type', 'unknown').replace('_', ' ').title()}
- **Language**: {structure.get('language', 'unknown').upper()}
- **Total Sections**: {len(chunks)}
- **Hierarchy Depth**: {structure.get('metadata', {}).get('max_depth', 'unknown')} levels

## Organization

This knowledge base uses intelligent, structure-aware chunking:

- Content is organized by **logical sections** (not arbitrary splits)
- Each chunk represents a **semantically complete unit**
- Hierarchical relationships are **preserved from the source**
- Navigation follows the **document's natural structure**

## Quick Navigation

- [View Hierarchical Index](index.md) - Browse all sections by structure
- [View Metadata](metadata.json) - Technical details and complete structure

## How to Use

When you ask questions about this content, Claude Code will:

1. **Automatically discover** this skill based on your query
2. **Navigate the hierarchy** to find relevant sections
3. **Access complete sections** for comprehensive answers
4. **Preserve context** from the document structure

## Structure Notes

{structure.get('metadata', {}).get('analyzer_notes', 'No additional notes.')}

## Content Access

All content is available in the `chunks/` directory, organized by semantic section IDs. Each chunk includes:

- Full hierarchical path
- Semantic type (e.g., chapter, procedure, article)
- Token count
- Complete section content

Browse the [hierarchical index](index.md) to explore the knowledge base structure.
"""

    skill_path = skill_dir / 'SKILL.md'
    with open(skill_path, 'w', encoding='utf-8') as f:
        f.write(skill_content)

    print(f"  Skill file created: {skill_path}")


def auto_calculate_estimated_tokens(structure_path: Path, workspace: Path) -> bool:
    """
    Automatically calculate estimated_tokens for all sections based on document density.

    Args:
        structure_path: Path to structure.json
        workspace: Analysis workspace path

    Returns:
        True if any tokens were auto-calculated, False otherwise
    """
    from semantic_analyzer import (
        load_structure,
        save_structure,
        calculate_document_density,
        estimate_tokens_by_lines
    )

    # Load structure
    structure = load_structure(structure_path)

    # Load source documents to calculate density
    samples_dir = workspace / 'samples'
    source_files = list(samples_dir.glob('*.txt'))

    if not source_files:
        print("⚠️  No source files found for density calculation")
        return False

    # Combine all sources for density calculation
    combined_content = ""
    for source_file in source_files:
        with open(source_file, 'r', encoding='utf-8') as f:
            combined_content += f.read() + "\n\n"

    # Calculate document density
    tokens_per_line = calculate_document_density(combined_content)

    # Recursively auto-calculate estimated_tokens for all sections
    def process_node(node):
        """Recursively process nodes and calculate estimated_tokens"""
        changes_made = False

        # Always calculate for this node (ensures consistency)
        if 'start_line' in node and 'end_line' in node:
            new_estimate = estimate_tokens_by_lines(
                node['start_line'],
                node['end_line'],
                tokens_per_line
            )
            # Update if different or missing
            if node.get('estimated_tokens') != new_estimate:
                node['estimated_tokens'] = new_estimate
                changes_made = True

        # Process children
        if 'children' in node:
            for child in node['children']:
                if process_node(child):
                    changes_made = True

        return changes_made

    # Process all sections in hierarchy
    any_changes = False
    for section in structure.get('hierarchy', []):
        if process_node(section):
            any_changes = True

    # Save if changes were made
    if any_changes:
        save_structure(structure, structure_path)
        print(f"✓ Auto-calculated estimated_tokens using density: {tokens_per_line:.2f} tokens/line")

    return any_changes


def create_subdivision_request(
    workspace: Path,
    oversized_sections: List[Dict],
    structure_path: Path,
    max_tokens: int
) -> Path:
    """
    Create subdivision request for Claude Code to analyze oversized sections.

    Args:
        workspace: Analysis workspace path
        oversized_sections: List of oversized section dictionaries
        structure_path: Path to structure.json
        max_tokens: Maximum tokens per chunk

    Returns:
        Path to subdivision request file
    """
    from semantic_analyzer import load_structure, extract_section_content, estimate_tokens

    # Load structure to get context
    structure = load_structure(structure_path)

    # Load source documents
    samples_dir = workspace / 'samples'
    source_files = list(samples_dir.glob('*.txt'))

    full_content = ""
    for source_file in source_files:
        with open(source_file, 'r', encoding='utf-8') as f:
            full_content += f.read() + "\n\n"

    # Create subdivision request
    request_file = workspace / 'SUBDIVISION_REQUEST.md'

    request_content = f"""# Semantic Subdivision Request

## Overview

The initial structure analysis identified **{len(oversized_sections)} section(s)** that exceed the {max_tokens} token target. These sections need to be semantically subdivided to improve knowledge base performance.

**Your task:** Analyze each oversized section below and create semantic subdivisions by adding `children` to the section in structure.json.

## Structure File

**Location:** `{structure_path}`

## Oversized Sections

The following sections need subdivision:

"""

    # Add details for each oversized section
    for i, section in enumerate(oversized_sections, 1):
        section_id = section['id']
        section_title = section['title']
        section_path = section['path']
        actual_tokens = section['actual_tokens']
        overage = actual_tokens - max_tokens

        request_content += f"""
### {i}. {section_title}

- **ID:** `{section_id}`
- **Path:** {section_path}
- **Current size:** {actual_tokens} tokens (exceeds limit by {overage} tokens)
- **Target:** ≤{max_tokens} tokens per subdivision

**Content preview:**

```
{section.get('preview', '(Content preview not available)')}
```

**Full content location:** See structure.json markers to extract full section content from source documents.

---
"""

    request_content += f"""

## Your Task: Semantic Subdivision

For each oversized section above, follow these steps:

### Step 1: Analyze Section Structure

1. **Locate the section** in structure.json by ID
2. **Extract full content** using the section's start_marker and end_marker:
   - Use extract_section_content() from semantic_analyzer.py
   - Or read from workspace samples and find markers
3. **Identify logical subdivisions** within the content:
   - What are the natural semantic boundaries?
   - For legal documents: Look for Incisos, Parágrafos, Alíneas
   - For technical docs: Look for subsections, numbered steps
   - For general text: Look for topic shifts, paragraph groups

### Step 2: Create Children Structure

Update structure.json to add `children` array to the oversized section. Each child should:
- Have a unique ID: `{{parent_id}}_{{index:03d}}` (e.g., `section_007_003_001`)
- Have a descriptive title
- Have accurate start_marker and end_marker (use next-section start as end marker)
- Be ≤{max_tokens} tokens when extracted
- Have `children: []` (initially empty, will subdivide again if needed)

**Example subdivision:**

```json
{{
  "id": "section_007_003",
  "title": "Art. 155 - ICMS",
  "level": 2,
  "semantic_type": "article",
  "start_marker": "Art. 155. Compete aos Estados",
  "end_marker": "Art. 156. Compete aos Municípios",
  "estimated_tokens": 8000,
  "children": [
    {{
      "id": "section_007_003_001",
      "title": "Art. 155 Caput",
      "level": 3,
      "semantic_type": "article_section",
      "start_marker": "Art. 155. Compete aos Estados",
      "end_marker": "§ 1º",
      "estimated_tokens": 1200,
      "children": []
    }},
    {{
      "id": "section_007_003_002",
      "title": "Art. 155 § 1º ao § 5º",
      "level": 3,
      "semantic_type": "article_section",
      "start_marker": "§ 1º",
      "end_marker": "§ 6º",
      "estimated_tokens": 2500,
      "children": []
    }},
    {{
      "id": "section_007_003_003",
      "title": "Art. 155 § 6º ao final",
      "level": 3,
      "semantic_type": "article_section",
      "start_marker": "§ 6º",
      "end_marker": "Art. 156. Compete aos Municípios",
      "estimated_tokens": 4300,
      "children": []
    }}
  ]
}}
```

### Step 3: Validate Markers (CRITICAL)

Before saving structure.json:
1. **Test extraction** for 2-3 of your new subdivisions
2. **Verify token counts** match your estimates
3. **Check for overlaps** between adjacent children
4. **Ensure markers are unique** and specific

### Step 4: Update structure.json

1. Find the oversized section by ID in structure.json
2. Replace its `children: []` with your new children array
3. Save the updated structure.json
4. Update `estimated_tokens` for the parent section if needed

### Step 5: Re-validate

After updating structure.json, the system will automatically re-validate when you run:

```bash
python3 generate_kb.py --name {structure['metadata'].get('kb_name', 'kb')} --analyze-only
```

The validation will:
- Check all new leaf sections against the {max_tokens} token limit
- Report any remaining oversized sections
- Create a new subdivision request if needed

## Important Notes

- **Semantic boundaries**: Subdivide based on MEANING, not arbitrary token counts
- **Complete units**: Each subdivision should be a complete logical unit
- **Preserve hierarchy**: Maintain document structure and relationships
- **Recursive process**: If subdivisions are still oversized, they'll be flagged for further subdivision
- **Atomic sections**: If a section truly cannot be subdivided (indivisible content), document this in metadata `analyzer_notes`

## Marker Best Practices

1. **Use next-section start as end marker** to avoid overlaps
2. **Include contextual text** for uniqueness (e.g., "§ 1º O imposto" not just "§ 1º")
3. **Validate markers exist** in source document using Grep
4. **Test extraction** before finalizing structure

## After Subdivision

Once you've updated structure.json:
1. The system will detect the changes
2. Validation will run automatically
3. Process repeats until all sections are ≤{max_tokens} tokens
4. When all valid, proceed to Phase 2 (skill generation)

---

**Ready to begin?** Start by analyzing the first oversized section above and updating structure.json with semantic subdivisions.
"""

    # Write request file
    with open(request_file, 'w', encoding='utf-8') as f:
        f.write(request_content)

    return request_file


def run_analysis_phase(
    name: str,
    sources: List[str],
    description: str,
    max_tokens: int,
    workspace: Path
) -> Path:
    """
    Phase 1: Interactive analysis with Claude Code to create structure.json

    Args:
        name: Knowledge base name
        sources: List of source document paths
        description: KB description
        max_tokens: Maximum tokens per chunk
        workspace: Analysis workspace path

    Returns:
        Path to generated structure.json
    """
    from semantic_analyzer import (
        create_structure_template,
        save_structure,
        extract_document_sample,
        estimate_tokens,
        calculate_document_density
    )

    print("\nProcessing source documents...")

    # Process all source documents
    documents = []
    combined_content = ""  # For density calculation

    for source_path in sources:
        print(f"\nReading: {source_path}")
        try:
            content, doc_type = process_document(source_path)
            tokens = estimate_tokens(content)
            print(f"  Type: {doc_type}, Tokens: {tokens}")

            documents.append({
                'path': source_path,
                'type': doc_type,
                'content': content,
                'tokens': tokens
            })

            # Combine for density calculation
            combined_content += content + "\n\n"

            # Save document to workspace for Claude to access
            doc_file = workspace / 'samples' / f"{Path(source_path).stem}.txt"
            with open(doc_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  Saved to workspace: {doc_file}")

        except Exception as e:
            print(f"  Error processing {source_path}: {str(e)}")
            continue

    if not documents:
        raise ValueError("No documents could be processed")

    # Calculate document density for automatic token estimation
    tokens_per_line = calculate_document_density(combined_content)
    total_lines = len(combined_content.split('\n'))
    print(f"\nDocument density: {tokens_per_line:.2f} tokens/line ({total_lines} total lines)")

    # Create analysis request file for Claude Code
    analysis_request_file = workspace / 'ANALYSIS_REQUEST.md'

    request_content = f"""# Knowledge Base Structure Analysis Request

## Task

You (Claude Code) are requested to analyze the source document(s) and create a semantic, hierarchical structure for this knowledge base.

## Knowledge Base Information

- **Name**: {name}
- **Description**: {description}
- **Target chunk size**: ~{max_tokens} tokens (flexible for semantic completeness)

## Source Documents

"""

    for doc in documents:
        request_content += f"""
### {Path(doc['path']).name}

- **Type**: {doc['type']}
- **Size**: {doc['tokens']} tokens
- **Location**: `{workspace / 'samples' / f"{Path(doc['path']).stem}.txt"}`

"""

    request_content += f"""

## Document Density (Automatic Token Estimation)

This document collection has an average density of **{tokens_per_line:.2f} tokens per line**.

**IMPORTANT**: You do NOT need to manually calculate `estimated_tokens` for each section!

The system will automatically estimate tokens for any section using:

```
estimated_tokens = (end_line - start_line) × {tokens_per_line:.2f}
```

**Your job**: Only provide `start_line` and `end_line` for each section. Token estimation is automatic!

**Example**:
```json
{{
  "id": "section_001",
  "title": "Introduction",
  "start_line": 0,
  "end_line": 50
  // estimated_tokens will be auto-calculated: 50 × {tokens_per_line:.2f} = {int(50 * tokens_per_line)} tokens
}}
```

Do NOT include `estimated_tokens` in your structure.json - it will be calculated automatically.

## Your Task: Progressive Refinement Analysis

Please perform a **progressive refinement analysis** to identify the logical, hierarchical structure of these documents.

### Strategy for Large Documents (>100K tokens)

If the source document(s) exceed 100,000 tokens (~65,000 words), use this strategic approach:

1. **Initial sampling** - Read strategically:
   - First 1000 lines (beginning)
   - Middle 500 lines (use offset)
   - Last 500 lines
   - Do NOT repeatedly read the entire document

2. **Identify structure patterns** from samples:
   - What markers define sections? (TÍTULO, Chapter, ###, etc.)
   - What is the hierarchical pattern?
   - Are there repetitive structures?

3. **Use targeted search** to find all section markers:
   - Use Grep tool to find all instances of structural markers
   - Example: `Grep(pattern="^(TÍTULO|CAPÍTULO|Art\\. \\d+)", output_mode="content")`
   - Verify marker uniqueness and count

4. **Validate marker candidates** before creating full structure:
   - Ensure markers are unique or contextually specific
   - Check that end markers come after start markers
   - Test extraction on 2-3 sample sections

5. **Progressive validation** - Build structure level by level:
   - Validate top-level structure first
   - Then subdivide one level at a time
   - Run validation at each level

**Important:** For large documents, efficiency is critical. Use targeted reads and searches instead of multiple full reads.

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

For sections that are too large (>~{max_tokens} tokens), identify logical subdivisions:
- What are the natural subsections?
- How does the document author organize this content?
- What are the semantic boundaries?

**Continue recursively** until:
- All leaf sections are ≤~{max_tokens} tokens, OR
- You reach atomic level (section cannot be meaningfully subdivided)

⚠️ **Important**: Do not stop at first-level subdivision if sections are still oversized. Keep subdividing recursively until leaf sections meet the token target.

### Step 3.5: Validate Marker Boundaries (CRITICAL)

Before creating the full structure.json, validate that your markers correctly delimit sections:

**Validation Protocol:**

1. **Pick 3-5 sample sections** from different parts of your planned structure
2. **Manually test extraction** for each sample:
   - Use extract_section_content() or similar to extract content between markers
   - Verify the extracted content matches your expectations
   - Check token count matches your estimate

3. **Check for overlaps** between adjacent sections:
   - Extract content for section N
   - Extract content for section N+1
   - Ensure no content appears in both extractions
   - Verify end_marker of N comes BEFORE start_marker of N+1 in the document

4. **Verify marker uniqueness**:
   - If using generic patterns (like "Art. 5"), ensure context makes them unique
   - Use Grep to check if markers appear multiple times
   - Add more context to markers if needed

5. **Test boundary cases**:
   - First section in document
   - Last section in document
   - Sections at different hierarchical levels

**If validation fails:** STOP and revise your markers. Do not proceed to create the full structure.json with invalid markers.

**Example validation check:**
```python
# Extract two adjacent sections
content_1 = extract_between("TÍTULO I", "TÍTULO II")
content_2 = extract_between("TÍTULO II", "TÍTULO III")

# Verify:
# - content_1 doesn't contain "TÍTULO II" content
# - content_2 starts at "TÍTULO II"
# - No overlap between sections
```

### Step 4: Create Structure JSON

**IMPORTANT**: Use **line numbers** as the primary extraction method. Line numbers eliminate ambiguity and ensure precise section extraction.

**How to get line numbers:**
1. Use Grep with `-n` flag to show line numbers:
   ```
   Grep(pattern="^TÍTULO", output_mode="content", -n=True)
   # Output: "249:TÍTULO II – Dos Direitos..."
   ```
2. Extract line number from output (249 in above example)
3. Store as `start_line` (0-indexed, so 249 becomes start_line: 248)

Output the complete hierarchical structure as JSON in this format:

```json
{{
  "document_type": "legal_document",
  "language": "pt-BR",
  "hierarchy": [
    {{
      "id": "section_001",
      "title": "PREÂMBULO",
      "level": 0,
      "semantic_type": "preamble",
      "start_line": 0,
      "end_line": 15,
      "start_marker": "Nós, representantes do povo brasileiro",  // Optional: for reference
      "estimated_tokens": 150,
      "children": []
    }},
    {{
      "id": "section_002",
      "title": "TÍTULO I – DOS PRINCÍPIOS FUNDAMENTAIS",
      "level": 1,
      "semantic_type": "title",
      "start_line": 16,
      "end_line": 50,
      "start_marker": "TÍTULO I",  // Optional: for reference
      "estimated_tokens": 800,
      "children": [
        {{
          "id": "section_002_001",
          "title": "Art. 1º",
          "level": 2,
          "semantic_type": "article",
          "start_line": 17,
          "end_line": 25,
          "start_marker": "Art. 1º A República Federativa",  // Optional: for reference
          "estimated_tokens": 120,
          "children": []
        }}
      ]
    }}
  ],
  "metadata": {{
    "total_sections": 156,
    "max_depth": 4,
    "analysis_date": "2025-11-03",
    "analyzer_notes": "Legal document with 4-level hierarchy. Line numbers are 0-indexed (line 1 in editor = line 0 in structure)."
  }}
}}
```

**Line Number Notes:**
- `start_line`: 0-indexed, inclusive (first line of section)
- `end_line`: 0-indexed, exclusive (first line of NEXT section)
- Example: `start_line: 10, end_line: 20` extracts lines 10-19 (10 lines total)
- `start_marker`: Optional field for human reference, NOT used for extraction

### Step 5: Validate Chunk Sizes

**CRITICAL**: Before finalizing structure.json, validate that all leaf sections (sections without children) are properly sized:

1. **Review all leaf sections** in your structure
2. **Check token estimates** against the ~{max_tokens} token target
3. **Identify oversized sections**: Any leaf section >~{max_tokens} tokens must be subdivided
4. **Subdivide if possible**:
   - Look for natural subsections within the oversized section
   - Add children to break it down further
   - Update parent to have children (it will no longer be a leaf)
5. **Document atomic sections**: If a section cannot be meaningfully subdivided and exceeds {max_tokens} tokens:
   - Note this in the `analyzer_notes` metadata
   - Explain why it cannot be split (e.g., "Article 123 is 7000 tokens but is a single indivisible legal text")
   - Keep it as-is (semantic completeness is prioritized over size)

**Validation Checklist**:
- [ ] All leaf sections reviewed for size
- [ ] Oversized sections (>{max_tokens} tokens) subdivided where possible
- [ ] Any atomic oversized sections documented in analyzer_notes
- [ ] Token estimates are accurate (not just placeholders)
- [ ] **Line number validation:** All sections have start_line and end_line defined
- [ ] **Line number validation:** No overlapping ranges (end_line of section N ≤ start_line of section N+1)
- [ ] **Line number validation:** All line numbers are within document bounds (0 to total_lines)

## Using Line Numbers (Preferred Method)

**Line numbers are the PRIMARY extraction method** because they eliminate all ambiguity.

### Benefits of Line Numbers:
- ✅ **100% precise** - No ambiguity, always extracts correct section
- ✅ **Faster extraction** - Direct line range, no marker search
- ✅ **Easier validation** - Simple range overlap checks
- ✅ **Better debugging** - "Check lines 123-456" is clear

### Optional: Marker Creation Best Practices

Markers are OPTIONAL and used only for human reference. If you choose to include them:

### Rule 1: Markers Must Be Unique and Specific

**BAD Example (ambiguous):**
```json
"start_marker": "CHAPTER 1",
"end_marker": "Section 3"  // Might appear in multiple chapters!
```

**GOOD Example (specific with context):**
```json
"start_marker": "CHAPTER 1: INTRODUCTION",
"end_marker": "CHAPTER 2: METHODOLOGY"  // Next chapter start
```

### Rule 2: Use Next-Section Start as End Marker (CRITICAL)

The most reliable way to avoid overlaps is to use the start marker of the NEXT section at the same level:

```json
{{
  "id": "section_001",
  "title": "TÍTULO I – Dos Princípios Fundamentais",
  "start_marker": "TÍTULO I",
  "end_marker": "TÍTULO II"  // Start of next TÍTULO, not an article number
}}
```

This ensures sections never overlap and boundaries are clean.

### Rule 3: Include Contextual Text for Repetitive Structures

For documents with repeated patterns (legal documents, numbered lists), include enough context to make markers unique:

**BAD (too generic for legal documents):**
```json
"start_marker": "Art. 5º",
"end_marker": "Art. 6º"
```

**GOOD (includes contextual text):**
```json
"start_marker": "Art. 5º Todos são iguais perante a lei",
"end_marker": "Art. 6º São direitos sociais"
```

### Rule 4: Handle End-of-Document Sections

For the last section in a document or hierarchy level, use `null` as end_marker or a clear final marker:

```json
{{
  "id": "section_last",
  "title": "Final Dispositions",
  "start_marker": "DISPOSIÇÕES FINAIS",
  "end_marker": null  // Extends to end of document
}}
```

### Important General Notes

- **Semantic boundaries**: Split based on MEANING, not just token count
- **Complete thoughts**: Each chunk should be a complete logical unit
- **Preserve hierarchy**: Maintain parent-child relationships as they exist in the document
- **Token-optimized**: Aim for ~{max_tokens} tokens but prioritize semantic completeness

## Example: Legal Document Structure (Constitution, Laws)

Legal documents require special attention due to repetitive structures and cross-references:

**Hierarchical structure example:**
```json
{{
  "id": "titulo_02",
  "title": "TÍTULO II – Dos Direitos e Garantias Fundamentais",
  "start_marker": "TÍTULO II",
  "end_marker": "TÍTULO III",  // Next TÍTULO, ensures clean boundary
  "children": [
    {{
      "id": "titulo_02_cap_01",
      "title": "CAPÍTULO I – Dos Direitos Individuais",
      "start_marker": "CAPÍTULO I",
      "end_marker": "CAPÍTULO II",  // Next CAPÍTULO
      "children": [
        {{
          "id": "titulo_02_cap_01_art_05",
          "title": "Art. 5º - Igualdade perante a lei",
          "start_marker": "Art. 5º Todos são iguais perante a lei",
          "end_marker": "Art. 6º São direitos sociais",  // Next article with context
          "children": []  // Leaf section
        }}
      ]
    }}
  ]
}}
```

**Key points for legal documents:**
- Use next-section headers as end markers (TÍTULO → TÍTULO, CAPÍTULO → CAPÍTULO)
- Include first words of article text for uniqueness ("Art. 5º Todos são...")
- Never use just article numbers as markers ("Art. 5º" appears in references!)
- Subdivide long articles into paragraphs if needed

## Common Pitfalls to Avoid

### 1. Reading Large Documents Multiple Times
- ❌ DON'T repeatedly read the entire document
- ✅ DO use strategic sampling + targeted Grep searches

### 2. Using Ambiguous or Generic Markers
- ❌ DON'T use patterns like "Section 1", "Art. 5", or "Chapter 2"
- ✅ DO include context: "Section 1: Introduction", "Art. 5º Todos são iguais"

### 3. Not Validating Markers Before Finalizing
- ❌ DON'T create full structure without testing markers on samples
- ✅ DO validate 3-5 sections before proceeding (Step 3.5)

### 4. Overlapping Section Boundaries
- ❌ DON'T use end markers that appear inside the section
- ✅ DO use next-section start as end marker to ensure clean boundaries

### 5. Estimating Tokens Without Actual Extraction
- ❌ DON'T guess token counts
- ✅ DO extract actual content between markers and calculate precise estimates

### 6. Ignoring Document-Specific Patterns
- ❌ DON'T apply generic structure to specialized documents
- ✅ DO analyze the specific hierarchical pattern (legal, technical, academic)

## Output

Save your structure analysis to: `{workspace / 'structure.json'}`

### Automatic Validation

**After you create structure.json, the script will automatically validate it** to ensure all leaf sections meet the token target.

The validation will:
- Check all leaf sections against the ~{max_tokens} token threshold
- Report any oversized sections that need subdivision
- Provide actionable feedback if issues are found

If validation detects oversized sections:
1. Review the reported sections
2. Update structure.json to subdivide them
3. The script will validate again

**Important:** If a section cannot be meaningfully subdivided (atomic section), document it in the `analyzer_notes` metadata explaining why it cannot be split.

---

**Ready? Read the documents and create the structure.json file.**
"""

    with open(analysis_request_file, 'w', encoding='utf-8') as f:
        f.write(request_content)

    print(f"\n{'='*60}")
    print("ANALYSIS REQUEST CREATED")
    print(f"{'='*60}")
    print(f"\nAnalysis request file: {analysis_request_file}")
    print("\nClaude Code should now:")
    print(f"1. Read the analysis request: {analysis_request_file}")
    print(f"2. Read the source documents in: {workspace / 'samples'}/")
    print("3. Perform progressive refinement analysis")
    print(f"4. Create structure.json at: {workspace / 'structure.json'}")
    print("\n" + "="*60)
    print("\n⚠️  WAITING FOR CLAUDE CODE TO COMPLETE ANALYSIS...")
    print("\nPlease read the analysis request and create the structure.json file.")
    print("This script will wait for structure.json to be created.")
    print()

    # Wait for Claude Code to create structure.json
    structure_path = workspace / 'structure.json'

    # For now, we'll return the expected path
    # In actual use, Claude Code will create this file
    return structure_path


def generate_from_structure(
    name: str,
    structure_file: str,
    output_dir: str = None
) -> str:
    """
    Phase 2: Generate knowledge base skill from structure.json

    Args:
        name: Knowledge base name
        structure_file: Path to structure.json
        output_dir: Output directory for skill

    Returns:
        Path to generated skill directory
    """
    from semantic_analyzer import (
        load_structure,
        validate_structure,
        extract_section_content,
        estimate_tokens
    )

    print(f"Loading structure from: {structure_file}")
    structure = load_structure(Path(structure_file))

    # Determine output directory
    if output_dir is None:
        if Path('.claude/skills').exists():
            output_dir = '.claude/skills'
        else:
            output_dir = str(Path.home() / '.claude' / 'skills')

    skill_dir = Path(output_dir) / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    chunks_dir = skill_dir / 'chunks'
    chunks_dir.mkdir(exist_ok=True)

    print(f"\nGenerating skill at: {skill_dir}")
    print(f"\nStructure metadata:")
    print(f"  Document type: {structure.get('document_type', 'unknown')}")
    print(f"  Language: {structure.get('language', 'unknown')}")
    print(f"  Total sections: {structure.get('metadata', {}).get('total_sections', 'unknown')}")
    print(f"  Max depth: {structure.get('metadata', {}).get('max_depth', 'unknown')}")

    # Load source documents from workspace
    workspace = Path(structure_file).parent
    samples_dir = workspace / 'samples'

    if not samples_dir.exists():
        raise ValueError(f"Samples directory not found: {samples_dir}")

    # Load all source documents
    print("\nLoading source documents...")
    source_documents = {}
    for sample_file in samples_dir.glob('*.txt'):
        print(f"  Loading: {sample_file.name}")
        with open(sample_file, 'r', encoding='utf-8') as f:
            source_documents[sample_file.stem] = f.read()

    if not source_documents:
        raise ValueError("No source documents found in workspace/samples/")

    # Combine all source content (for multi-source KBs)
    full_content = '\n\n'.join(source_documents.values())

    print(f"\nExtracting chunks from structure...")

    # Collect all sections (flattened)
    all_chunks = []

    def process_section_hierarchy(node, parent_path="", depth=0):
        """Recursively process sections and create chunks"""
        nonlocal all_chunks

        # Build hierarchical path
        current_path = f"{parent_path} > {node['title']}" if parent_path else node['title']

        # Extract content for this section
        # Prefer start_line/end_line if available for more accurate extraction
        start_line = node.get('start_line')
        end_line = node.get('end_line')
        start_marker = node.get('start_marker', '')
        end_marker = node.get('end_marker')

        try:
            if start_line is not None and end_line is not None:
                # Use line-based extraction (more accurate)
                lines = full_content.split('\n')
                content_lines = lines[start_line:end_line]
                content = '\n'.join(content_lines)
                start_pos = len('\n'.join(lines[:start_line]))
                end_pos = start_pos + len(content)
            else:
                # Fallback to marker-based extraction
                content, start_pos, end_pos = extract_section_content(
                    full_content,
                    start_marker,
                    end_marker,
                    include_markers=True
                )

            # Estimate actual tokens
            actual_tokens = estimate_tokens(content)

            # Create chunk entry
            chunk = {
                'id': node['id'],
                'title': node['title'],
                'path': current_path,
                'level': node.get('level', depth),
                'semantic_type': node.get('semantic_type', 'section'),
                'content': content,
                'tokens': actual_tokens,
                'start_pos': start_pos,
                'end_pos': end_pos,
                'has_children': len(node.get('children', [])) > 0
            }

            all_chunks.append(chunk)

            print(f"  [{node['id']}] {node['title']} ({actual_tokens} tokens)")

        except Exception as e:
            print(f"  ⚠️  Error extracting {node['id']} - {node['title']}: {str(e)}")

        # Process children
        for i, child in enumerate(node.get('children', [])):
            process_section_hierarchy(child, current_path, depth + 1)

    # Process all top-level sections
    for section in structure.get('hierarchy', []):
        process_section_hierarchy(section)

    print(f"\nTotal chunks extracted: {len(all_chunks)}")

    # Write chunk files (only for leaf nodes)
    print("\nWriting chunk files...")
    leaf_chunks_written = 0
    for chunk in all_chunks:
        # Skip parent nodes - only write leaf chunks
        if chunk['has_children']:
            continue

        leaf_chunks_written += 1
        chunk_filename = f"{chunk['id']}.md"
        chunk_path = chunks_dir / chunk_filename

        # Build breadcrumb
        breadcrumb = chunk['path']

        chunk_content = f"""# {chunk['title']}

**Path:** {breadcrumb}
**Type:** {chunk['semantic_type']}
**Tokens:** ~{chunk['tokens']}
**Level:** {chunk['level']}

---

{chunk['content']}
"""

        with open(chunk_path, 'w', encoding='utf-8') as f:
            f.write(chunk_content)

    # Create metadata file
    print("\nGenerating metadata...")
    metadata = {
        'name': name,
        'description': structure.get('metadata', {}).get('analyzer_notes', ''),
        'structure': structure,
        'total_chunks': len(all_chunks),
        'chunks': [
            {
                'id': chunk['id'],
                'title': chunk['title'],
                'path': chunk['path'],
                'level': chunk['level'],
                'semantic_type': chunk['semantic_type'],
                'tokens': chunk['tokens'],
                'file': f"{chunk['id']}.md",
                'has_children': chunk['has_children']
            }
            for chunk in all_chunks
        ]
    }

    metadata_path = skill_dir / 'metadata.json'
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # Generate hierarchical index
    print("Generating hierarchical index...")
    create_hierarchical_index(skill_dir, structure, all_chunks)

    # Create main SKILL.md
    print("Creating skill file...")
    create_semantic_skill_file(skill_dir, name, structure, all_chunks)

    print(f"\n✓ Skill generation complete!")
    print(f"✓ Created {leaf_chunks_written} leaf chunks (out of {len(all_chunks)} total sections)")
    print(f"✓ Skipped {len(all_chunks) - leaf_chunks_written} parent nodes (no duplication)")

    return str(skill_dir)


def main():
    parser = argparse.ArgumentParser(
        description='Generate a discoverable knowledge base skill from documents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Two-Phase Workflow (Semantic Analysis):

  Phase 1 - Analyze document structure:
  %(prog)s --name "my-kb" --sources document.pdf --description "My knowledge base" --analyze-only

  [Then Claude Code reads analysis request and creates structure.json]

  Phase 2 - Generate skill from structure:
  %(prog)s --name "my-kb" --from-structure ".claude/skills/my-kb_analysis/structure.json"

Examples:

  # Brazilian Constitution knowledge base
  %(prog)s --name "constituicao-br" --sources constitution.pdf \\
    --description "Brazilian Federal Constitution" --analyze-only

  # Multi-source technical documentation
  %(prog)s --name "product-docs" --sources manual.pdf api.md guide.txt \\
    --description "Complete product documentation" --analyze-only

  # Generate from completed analysis
  %(prog)s --name "product-docs" --from-structure "./product-docs_analysis/structure.json"
        """
    )

    parser.add_argument(
        '--name',
        required=True,
        help='Name of the knowledge base skill (lowercase, hyphens only, max 64 chars)'
    )

    parser.add_argument(
        '--sources',
        nargs='+',
        help='One or more source document paths (PDF, MD, TXT)'
    )

    parser.add_argument(
        '--description',
        help='Description of what this knowledge base contains (max 1024 chars)'
    )

    # Two-phase operation modes
    parser.add_argument(
        '--analyze-only',
        action='store_true',
        help='Phase 1: Analyze documents and output structure.json only (requires Claude Code interaction)'
    )

    parser.add_argument(
        '--from-structure',
        type=str,
        metavar='STRUCTURE_FILE',
        help='Phase 2: Generate skill from existing structure.json file'
    )

    parser.add_argument(
        '--max-tokens',
        type=int,
        default=5000,
        help='Maximum tokens per chunk (default: 5000)'
    )

    parser.add_argument(
        '--output-dir',
        help='Output directory for the skill (default: .claude/skills/)'
    )

    args = parser.parse_args()

    # Validate argument combinations
    if args.from_structure:
        # Phase 2: Generate from structure mode
        if not Path(args.from_structure).exists():
            print(f"Error: Structure file not found: {args.from_structure}", file=sys.stderr)
            sys.exit(1)
    else:
        # Phase 1 or legacy mode: require sources and description
        if not args.sources or not args.description:
            parser.error("--sources and --description are required unless using --from-structure")

    try:
        if args.analyze_only:
            # Phase 1: Analysis only mode
            print("=" * 60)
            print("PHASE 1: SEMANTIC ANALYSIS MODE")
            print("=" * 60)
            print("\nThis mode requires Claude Code to perform semantic analysis.")
            print("The script will create analysis requests that Claude Code should respond to.")
            print("\nNote: This is an interactive process. Claude Code must be actively")
            print("      involved to analyze document structure and create structure.json")
            print()

            # Import semantic analyzer
            from semantic_analyzer import create_analysis_workspace

            # Create analysis workspace
            workspace = create_analysis_workspace(args.name, args.output_dir)
            print(f"Analysis workspace created: {workspace}")

            # Start analysis phase
            structure_path = run_analysis_phase(
                name=args.name,
                sources=args.sources,
                description=args.description,
                max_tokens=args.max_tokens,
                workspace=workspace
            )

            # Automatically validate structure if it exists
            if structure_path.exists():
                # Auto-calculate estimated_tokens for sections that don't have it
                print(f"\n{'=' * 60}")
                print("AUTO-CALCULATING ESTIMATED TOKENS")
                print(f"{'=' * 60}")
                print()
                auto_calculate_estimated_tokens(structure_path, workspace)

                print(f"\n{'=' * 60}")
                print("VALIDATING STRUCTURE")
                print(f"{'=' * 60}")
                print()

                # Import validation function
                sys.path.insert(0, str(Path(__file__).parent))
                from validate_structure import validate_structure

                all_valid, valid_sections, oversized_sections = validate_structure(
                    structure_path,
                    max_tokens=args.max_tokens,
                    verbose=False
                )

                # If oversized sections found, create subdivision request
                if not all_valid and oversized_sections:
                    print(f"\n{'=' * 60}")
                    print("SEMANTIC SUBDIVISION REQUIRED")
                    print(f"{'=' * 60}")
                    print()
                    print(f"⚠️  Found {len(oversized_sections)} oversized section(s) that need subdivision.")
                    print()

                    # Create subdivision request for Claude Code
                    subdivision_request = create_subdivision_request(
                        workspace=workspace,
                        oversized_sections=oversized_sections,
                        structure_path=structure_path,
                        max_tokens=args.max_tokens
                    )

                    print(f"📝 Subdivision request created: {subdivision_request}")
                    print()
                    print("NEXT STEPS:")
                    print("1. Read the subdivision request above")
                    print("2. Analyze oversized sections and determine semantic subdivisions")
                    print("3. Update structure.json by adding 'children' to oversized sections")
                    print(f"4. Re-run validation: python3 {sys.argv[0]} --name '{args.name}' --analyze-only")
                    print()
                    print("This process will repeat until all leaf sections are ≤{} tokens.".format(args.max_tokens))
                    print()
            else:
                print(f"\n⚠️  Note: structure.json not yet created.")
                print(f"After creating {structure_path}, validation will run automatically.")

            print(f"\n{'=' * 60}")
            print("ANALYSIS COMPLETE!")
            print(f"{'=' * 60}")
            print(f"\nStructure file created: {structure_path}")
            print("\nTo generate the knowledge base skill, run:")
            print(f"  python3 {sys.argv[0]} --name '{args.name}' --from-structure '{structure_path}'")
            print()

        elif args.from_structure:
            # Phase 2: Generate from structure mode
            print("=" * 60)
            print("PHASE 2: SKILL GENERATION FROM STRUCTURE")
            print("=" * 60)
            print()

            # Validate structure before generating
            print("=" * 60)
            print("VALIDATING STRUCTURE")
            print("=" * 60)
            print()

            sys.path.insert(0, str(Path(__file__).parent))
            from validate_structure import validate_structure

            all_valid, valid_sections, oversized_sections = validate_structure(
                Path(args.from_structure),
                max_tokens=args.max_tokens,
                verbose=False
            )

            if not all_valid:
                print(f"\n{'=' * 60}")
                print("SEMANTIC SUBDIVISION RECOMMENDED")
                print(f"{'=' * 60}")
                print()
                print(f"⚠️  Warning: Structure has {len(oversized_sections)} oversized section(s).")
                print()

                # Get workspace path from structure file
                structure_path = Path(args.from_structure)
                workspace = structure_path.parent

                # Create subdivision request for Claude Code
                subdivision_request = create_subdivision_request(
                    workspace=workspace,
                    oversized_sections=oversized_sections,
                    structure_path=structure_path,
                    max_tokens=args.max_tokens
                )

                print(f"📝 Subdivision request created: {subdivision_request}")
                print()
                print("NEXT STEPS:")
                print("1. Read the subdivision request to understand which sections are oversized")
                print("2. Analyze oversized sections and determine semantic subdivisions")
                print("3. Update structure.json by adding 'children' to oversized sections")
                print(f"4. Re-run Phase 2: python3 {sys.argv[0]} --name '{args.name}' --from-structure '{args.from_structure}'")
                print()
                print("OR proceed with generation (oversized sections may impact performance):")
                print()
                import time
                for i in range(5, 0, -1):
                    print(f"  Continuing in {i} seconds... (Ctrl+C to cancel)", end='\r')
                    time.sleep(1)
                print()
                print("Proceeding with generation...")
                print()

            skill_path = generate_from_structure(
                name=args.name,
                structure_file=args.from_structure,
                output_dir=args.output_dir
            )

            print(f"\n{'=' * 60}")
            print("SKILL GENERATION COMPLETE!")
            print(f"{'=' * 60}")
            print(f"\nSkill location: {skill_path}")
            print("\nClaude Code will automatically discover and use this skill when relevant.")
            print()

        else:
            # No mode specified - show usage help
            parser.print_help()
            print("\n" + "=" * 60)
            print("ERROR: Must specify operation mode")
            print("=" * 60)
            print("\nKnowledge base generation requires semantic analysis.")
            print("\nPlease choose one of:")
            print("  --analyze-only     : Start Phase 1 (semantic analysis)")
            print("  --from-structure   : Start Phase 2 (generate from structure.json)")
            print("\nExample two-phase workflow:")
            print("  1. python3", sys.argv[0], "--name kb --sources doc.pdf --description '...' --analyze-only")
            print("  2. [Claude Code creates structure.json]")
            print("  3. python3", sys.argv[0], "--name kb --from-structure structure.json")
            sys.exit(1)

    except Exception as e:
        print(f"\nError: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
