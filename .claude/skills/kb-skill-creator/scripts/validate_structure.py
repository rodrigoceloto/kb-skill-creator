#!/usr/bin/env python3
"""
Validate structure.json for chunk size compliance.

This script checks that all leaf sections in a structure.json file
are within the target token size (~5000 tokens by default).
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Import from semantic_analyzer
try:
    from semantic_analyzer import estimate_tokens, extract_section_content
except ImportError:
    print("Error: semantic_analyzer.py not found. Run from scripts/ directory.")
    sys.exit(1)


def load_structure(structure_path: Path) -> Dict:
    """Load and parse structure.json"""
    with open(structure_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def collect_leaf_sections(node: Dict, parent_path: str = "", leaf_sections: List = None) -> List[Dict]:
    """
    Recursively collect all leaf sections (sections without children).

    Args:
        node: Current section node
        parent_path: Hierarchical path to this node
        leaf_sections: Accumulated list of leaf sections

    Returns:
        List of leaf section info dicts
    """
    if leaf_sections is None:
        leaf_sections = []

    current_path = f"{parent_path} > {node['title']}" if parent_path else node['title']

    # Check if this is a leaf (no children)
    children = node.get('children', [])
    if not children:
        leaf_sections.append({
            'id': node['id'],
            'title': node['title'],
            'path': current_path,
            'level': node.get('level', 0),
            'semantic_type': node.get('semantic_type', 'section'),
            'start_marker': node.get('start_marker', ''),
            'end_marker': node.get('end_marker'),
            'start_line': node.get('start_line'),
            'end_line': node.get('end_line'),
            'estimated_tokens': node.get('estimated_tokens', 0)
        })
    else:
        # Process children
        for child in children:
            collect_leaf_sections(child, current_path, leaf_sections)

    return leaf_sections


def validate_structure(
    structure_path: Path,
    max_tokens: int = 5000,
    verbose: bool = False
) -> Tuple[bool, List[Dict], List[Dict]]:
    """
    Validate all leaf sections in structure.json against token threshold.

    Args:
        structure_path: Path to structure.json
        max_tokens: Maximum tokens per leaf section
        verbose: Print detailed validation info

    Returns:
        Tuple of (all_valid, valid_sections, oversized_sections)
    """
    print(f"Validating: {structure_path}")
    print(f"Max tokens per leaf section: {max_tokens}")
    print()

    # Load structure
    structure = load_structure(structure_path)

    # Load source documents from workspace
    workspace = structure_path.parent
    samples_dir = workspace / 'samples'

    if not samples_dir.exists():
        print(f"Error: Samples directory not found: {samples_dir}")
        print("Structure validation requires source documents in workspace/samples/")
        return False, [], []

    # Load all source documents
    source_documents = {}
    for sample_file in samples_dir.glob('*.txt'):
        with open(sample_file, 'r', encoding='utf-8') as f:
            source_documents[sample_file.stem] = f.read()

    if not source_documents:
        print(f"Error: No source documents found in {samples_dir}")
        return False, [], []

    # Combine all source content
    full_content = '\n\n'.join(source_documents.values())

    # Collect all leaf sections
    all_leaf_sections = []
    for section in structure.get('hierarchy', []):
        collect_leaf_sections(section, "", all_leaf_sections)

    print(f"Found {len(all_leaf_sections)} leaf sections to validate")
    print()

    # Validate each leaf section
    valid_sections = []
    oversized_sections = []

    for leaf in all_leaf_sections:
        try:
            # Extract actual content using line numbers (REQUIRED)
            start_line = leaf.get('start_line')
            end_line = leaf.get('end_line')

            if start_line is None or end_line is None:
                raise ValueError(
                    f"Section '{leaf['id']}' missing required fields: start_line and/or end_line. "
                    f"Line numbers are required for extraction. Please update structure.json to include "
                    f"'start_line' and 'end_line' for all sections."
                )

            # Line-based extraction (precise and unambiguous)
            from semantic_analyzer import extract_by_line_numbers
            content, actual_tokens = extract_by_line_numbers(
                full_content,
                start_line,
                end_line
            )

            # Check against threshold
            is_valid = actual_tokens <= max_tokens

            # Add content preview (first 200 chars) for reference
            preview = content[:200].strip() + "..." if len(content) > 200 else content.strip()

            validation_result = {
                **leaf,
                'actual_tokens': actual_tokens,
                'estimated_tokens': leaf['estimated_tokens'],
                'is_valid': is_valid,
                'overflow': max(0, actual_tokens - max_tokens),
                'preview': preview  # For human reference in subdivision requests
            }

            if is_valid:
                valid_sections.append(validation_result)
                if verbose:
                    print(f"✓ {leaf['id']} ({actual_tokens} tokens) - OK")
            else:
                oversized_sections.append(validation_result)
                print(f"✗ {leaf['id']} ({actual_tokens} tokens) - OVERSIZED by {validation_result['overflow']} tokens")
                print(f"  Path: {leaf['path']}")
                print(f"  Type: {leaf['semantic_type']}")
                print(f"  Suggestion: Subdivide this section into smaller logical units")
                print()

        except Exception as e:
            print(f"⚠️  Error validating {leaf['id']}: {str(e)}")
            oversized_sections.append({
                **leaf,
                'actual_tokens': 0,
                'is_valid': False,
                'error': str(e)
            })

    # Summary
    print()
    print("="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    print(f"Total leaf sections: {len(all_leaf_sections)}")
    print(f"Valid sections (≤{max_tokens} tokens): {len(valid_sections)}")
    print(f"Oversized sections: {len(oversized_sections)}")

    if oversized_sections:
        print()
        print("Oversized sections require subdivision:")
        for section in oversized_sections:
            if 'error' not in section:
                print(f"  • {section['id']}: {section['actual_tokens']} tokens (over by {section['overflow']})")

    all_valid = len(oversized_sections) == 0

    print()
    if all_valid:
        print("✓ All leaf sections are within token limit!")
    else:
        print(f"✗ {len(oversized_sections)} section(s) need subdivision")
        print()
        print("Next steps:")
        print("1. Review oversized sections listed above")
        print("2. Identify natural subdivisions within each oversized section")
        print("3. Update structure.json to add children to these sections")
        print("4. Run validation again to verify")

    return all_valid, valid_sections, oversized_sections


def main():
    """Main entry point for validation script"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Validate structure.json chunk sizes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:

  Validate structure.json in analysis workspace:
  %(prog)s .claude/skills/my-kb_analysis/structure.json

  Use custom token threshold:
  %(prog)s structure.json --max-tokens 3000

  Verbose output (show all sections):
  %(prog)s structure.json --verbose
"""
    )

    parser.add_argument(
        'structure_file',
        type=str,
        help='Path to structure.json file'
    )

    parser.add_argument(
        '--max-tokens',
        type=int,
        default=5000,
        help='Maximum tokens per leaf section (default: 5000)'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show validation details for all sections'
    )

    args = parser.parse_args()

    structure_path = Path(args.structure_file)

    if not structure_path.exists():
        print(f"Error: Structure file not found: {structure_path}")
        sys.exit(1)

    all_valid, valid_sections, oversized_sections = validate_structure(
        structure_path,
        max_tokens=args.max_tokens,
        verbose=args.verbose
    )

    # Exit with appropriate code
    sys.exit(0 if all_valid else 1)


if __name__ == '__main__':
    main()
