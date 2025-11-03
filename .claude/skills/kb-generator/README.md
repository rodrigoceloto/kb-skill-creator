# Knowledge Base Generator Skill

Generate discoverable, structure-aware knowledge base skills from document sources.

## Overview

This skill creates new Claude Code skills from documentation sources (PDF, Markdown, text files). Unlike mechanical chunking that splits text arbitrarily, this generator uses **intelligent, structure-aware parsing** to preserve the logical organization of your documents.

## Features

- **Structure-Aware Chunking**: Respects document hierarchy (chapters, sections, subsections)
- **Multiple Format Support**: PDF, Markdown, and plain text
- **Hierarchical Navigation**: Browse content by its natural structure
- **Automatic Discovery**: Generated skills are automatically discovered by Claude Code
- **Token-Optimized**: Chunks respect ~5000 token limits while maintaining logical boundaries

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. The skill is ready to use - Claude Code will automatically discover it.

## Usage

### Basic Usage

Create a knowledge base from a single document:

```bash
python3 .claude/skills/kb-generator/scripts/generate_kb.py \
  --name "my-knowledge-base" \
  --sources "/path/to/document.pdf" \
  --description "Description of what this knowledge base contains"
```

### Multiple Sources

Combine multiple documents into one knowledge base:

```bash
python3 .claude/skills/kb-generator/scripts/generate_kb.py \
  --name "product-docs" \
  --sources manual.pdf guide.md reference.txt \
  --description "Complete product documentation including manual, guide, and reference"
```

### Custom Token Limit

Adjust the maximum tokens per chunk:

```bash
python3 .claude/skills/kb-generator/scripts/generate_kb.py \
  --name "large-manual" \
  --sources manual.pdf \
  --description "Large technical manual" \
  --max-tokens 3000
```

## Examples

### Example 1: Car Manual

```bash
python3 .claude/skills/kb-generator/scripts/generate_kb.py \
  --name "corolla-hybrid-2025-manual" \
  --sources "Toyota_Corolla_Hybrid_2025_Manual.pdf" \
  --description "Complete owner's manual for Toyota Corolla Hybrid 2025 including maintenance, features, and troubleshooting"
```

This creates a skill that Claude will automatically use when you ask questions like:
- "How do I change the oil in my Corolla Hybrid 2025?"
- "What's the tire pressure for the Corolla Hybrid?"
- "How does the hybrid system work?"

### Example 2: API Documentation

```bash
python3 .claude/skills/kb-generator/scripts/generate_kb.py \
  --name "api-reference" \
  --sources "api-overview.md" "endpoints.md" "authentication.md" \
  --description "Complete API reference documentation including endpoints, authentication, and examples"
```

## How It Works

### 1. Document Parsing

The generator analyzes your documents to detect their logical structure:

**For Markdown files:**
- Parses `#` heading levels
- Maintains parent-child relationships
- Preserves hierarchy

**For PDF and text files:**
- Detects numbered sections (1.1, 1.2, etc.)
- Identifies UPPERCASE HEADINGS
- Recognizes Chapter/Section keywords
- Falls back to paragraph-based splitting when needed

### 2. Structure-Based Chunking

Instead of mechanically splitting at token boundaries, the generator:
- Creates chunks based on logical sections
- Keeps related content together
- Only splits sections that exceed the token limit
- Preserves context and hierarchy

### 3. Generated Structure

Each knowledge base skill contains:

```
kb-name/
├── SKILL.md              # Main skill file (auto-discovered by Claude)
├── index.md              # Hierarchical table of contents
├── metadata.json         # Technical metadata
├── chunks/               # Individual content sections
│   ├── chunk_001.md     # First section
│   ├── chunk_002.md     # Second section
│   └── ...
└── README.md            # (optional) Custom readme
```

### 4. Navigation

Each chunk includes:
- Hierarchical path (e.g., "Chapter 1 > Safety > Warnings")
- Source document name
- Token count
- Section level
- Complete content for that section

## Advanced Usage

### Custom Output Directory

```bash
python3 .claude/skills/kb-generator/scripts/generate_kb.py \
  --name "my-kb" \
  --sources doc.pdf \
  --description "My knowledge base" \
  --output-dir "/custom/path/to/skills"
```

### Processing Multiple Related Documents

Create a comprehensive knowledge base from an entire documentation set:

```bash
python3 .claude/skills/kb-generator/scripts/generate_kb.py \
  --name "complete-product-docs" \
  --sources \
    "00-overview.md" \
    "01-getting-started.md" \
    "02-installation.md" \
    "03-configuration.md" \
    "04-api-reference.pdf" \
    "05-troubleshooting.md" \
  --description "Complete product documentation from overview to troubleshooting"
```

## Parameters Reference

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--name` | Yes | Skill name (lowercase, hyphens, max 64 chars) |
| `--sources` | Yes | One or more document paths |
| `--description` | Yes | What the knowledge base contains (max 1024 chars) |
| `--max-tokens` | No | Max tokens per chunk (default: 5000) |
| `--output-dir` | No | Output directory (default: `.claude/skills/`) |

## Tips for Best Results

1. **Choose descriptive names**: The skill name should reflect the content (e.g., `python-stdlib-docs`, not `docs-1`)

2. **Write clear descriptions**: This helps Claude discover the skill automatically. Be specific about what the knowledge base contains.

3. **Organize related documents**: If you have multiple related documents, combine them into one knowledge base rather than creating separate skills.

4. **Check the generated index**: After creation, review `index.md` to ensure the structure was parsed correctly.

5. **For PDFs**: Better results with PDFs that have clear structure (numbered sections, consistent formatting)

6. **For Markdown**: Use proper heading hierarchy (`#`, `##`, `###`) for best structure detection

## Troubleshooting

### PDF text extraction issues

If PDF extraction fails or produces poor results:
- Ensure PDF is not encrypted or password-protected
- Try converting PDF to text first if it's an image-based PDF
- Check that pypdf is installed: `pip install pypdf`

### No sections detected

If the generator creates only one large chunk:
- Check that your document has clear section markers
- For text files, add clear headings or use numbered sections
- Consider converting to Markdown with proper `#` headings

### Script not found error

Make sure to run from the project directory or use the full path:
```bash
python3 /Users/rodrigoceloto/Projects/skills/.claude/skills/kb-generator/scripts/generate_kb.py --name ...
```

## License

This skill is part of the Claude Code skills ecosystem.
