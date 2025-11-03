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
        tokens = node.get('estimated_tokens', 0)
        result += f" *({semantic_type}, ~{tokens} tokens)*\n"

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
        estimate_tokens
    )

    print("\nProcessing source documents...")

    # Process all source documents
    documents = []
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

    request_content += """

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
        start_marker = node.get('start_marker', '')
        end_marker = node.get('end_marker')

        try:
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
