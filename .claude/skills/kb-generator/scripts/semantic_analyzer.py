#!/usr/bin/env python3
"""
Semantic Analyzer for Knowledge Base Generator
Provides helper functions for Claude Code to perform document structure analysis
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import hashlib


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.
    Uses a simple approximation: ~4 characters per token for English text.
    For more accuracy, consider using tiktoken library.
    """
    return len(text) // 4


def calculate_document_density(full_text: str) -> float:
    """
    Calculate average tokens per line for a document.

    This allows automatic token estimation based on line ranges without
    needing to extract and count tokens for each section individually.

    Args:
        full_text: Complete document text

    Returns:
        Average tokens per line (float)

    Example:
        density = calculate_document_density(document)
        # Returns: 42.5 tokens/line
        # Can then estimate: section_tokens = (end_line - start_line) * 42.5
    """
    lines = full_text.split('\n')
    total_lines = len(lines)
    if total_lines == 0:
        return 0.0

    total_tokens = estimate_tokens(full_text)
    return total_tokens / total_lines


def estimate_tokens_by_lines(
    start_line: int,
    end_line: int,
    tokens_per_line: float
) -> int:
    """
    Estimate tokens based on line range and document density.

    This is much faster than extracting content and counting tokens,
    and provides consistent estimates across all sections based on
    the document's actual characteristics.

    Args:
        start_line: Starting line number (0-indexed, inclusive)
        end_line: Ending line number (0-indexed, exclusive)
        tokens_per_line: Document density (from calculate_document_density)

    Returns:
        Estimated token count (int)

    Example:
        # Document has 45.3 tokens/line average
        estimated = estimate_tokens_by_lines(100, 250, 45.3)
        # Returns: (250 - 100) * 45.3 = 6795 tokens
    """
    if start_line >= end_line:
        return 0

    line_count = end_line - start_line
    return int(line_count * tokens_per_line)


def extract_document_sample(text: str, sample_size: int = 10000) -> Dict[str, str]:
    """
    Extract representative samples from document for structure detection.
    Returns beginning, middle, and end samples.

    Args:
        text: Full document text
        sample_size: Token count for each sample (default: 10000)

    Returns:
        Dictionary with 'beginning', 'middle', 'end' samples
    """
    char_size = sample_size * 4  # Convert tokens to approximate characters

    total_length = len(text)

    # Extract samples
    beginning = text[:char_size]

    middle_start = max(0, (total_length // 2) - (char_size // 2))
    middle_end = middle_start + char_size
    middle = text[middle_start:middle_end]

    end = text[-char_size:] if total_length > char_size else text

    return {
        'beginning': beginning,
        'middle': middle,
        'end': end,
        'total_tokens': estimate_tokens(text),
        'sample_tokens': estimate_tokens(beginning + middle + end)
    }


def normalize_whitespace_for_matching(text: str) -> str:
    """
    Normalize whitespace in text for robust marker matching.
    Collapses multiple spaces/tabs/newlines into single spaces.

    Args:
        text: Text to normalize

    Returns:
        Normalized text with single spaces
    """
    return re.sub(r'\s+', ' ', text.strip())


def find_marker_position(full_text: str, marker: str, start_from: int = 0) -> int:
    """
    Find marker position in text with whitespace normalization.

    Args:
        full_text: Text to search in
        marker: Marker text to find
        start_from: Position to start searching from

    Returns:
        Position of marker in full_text, or -1 if not found
    """
    # First try exact match (fast path)
    exact_pos = full_text.find(marker, start_from)
    if exact_pos != -1:
        return exact_pos

    # If exact match fails, try normalized matching
    # Create regex pattern that allows flexible whitespace
    # Escape special regex characters in the marker
    escaped_marker = re.escape(marker)
    # Replace escaped spaces with flexible whitespace pattern
    flexible_pattern = escaped_marker.replace(r'\ ', r'\s+')

    try:
        match = re.search(flexible_pattern, full_text[start_from:], re.MULTILINE)
        if match:
            return start_from + match.start()
    except re.error:
        # If regex fails, fall back to normalized string search
        normalized_marker = normalize_whitespace_for_matching(marker)

        # Search through text in chunks to find normalized match
        search_pos = start_from
        while search_pos < len(full_text):
            # Extract a window of text that could contain the marker
            window_size = len(marker) * 3  # Allow for extra whitespace
            window_end = min(search_pos + window_size, len(full_text))
            window = full_text[search_pos:window_end]

            normalized_window = normalize_whitespace_for_matching(window)

            if normalized_marker in normalized_window:
                # Found a potential match, now find exact position
                # Search character by character to find where match starts
                for offset in range(len(window)):
                    test_window = full_text[search_pos + offset:window_end]
                    if normalize_whitespace_for_matching(test_window).startswith(normalized_marker):
                        return search_pos + offset

            # Move search position forward
            search_pos += max(1, window_size // 2)

    return -1


def extract_section_content(
    full_text: str,
    start_marker: str,
    end_marker: Optional[str] = None,
    include_markers: bool = True
) -> Tuple[str, int, int]:
    """
    Extract content between start and end markers from text.
    Uses whitespace-normalized matching to handle spacing variations.

    Args:
        full_text: Complete document text
        start_marker: Text pattern marking section start
        end_marker: Text pattern marking section end (if None, goes to next start_marker or EOF)
        include_markers: Whether to include the markers in extracted content

    Returns:
        Tuple of (extracted_content, start_position, end_position)
    """
    # Find start position with whitespace normalization
    start_pos = find_marker_position(full_text, start_marker)
    if start_pos == -1:
        raise ValueError(f"Start marker not found: {start_marker[:50]}...")

    # Find end position
    if end_marker:
        end_pos = find_marker_position(full_text, end_marker, start_pos + len(start_marker))
        if end_pos == -1:
            # If end marker not found, take until end of document
            end_pos = len(full_text)
        elif not include_markers:
            # If not including markers, end before the end marker
            pass
        else:
            # Include the end marker (need to find actual length in document)
            # Find where the end marker actually ends in the text
            marker_start = end_pos
            marker_end = marker_start + len(end_marker)
            # Extend to cover any whitespace variations
            while marker_end < len(full_text) and full_text[marker_end].isspace():
                if full_text[marker_end] == '\n':
                    break  # Stop at newline
                marker_end += 1
            end_pos = marker_end
    else:
        # No end marker specified, take until end
        end_pos = len(full_text)

    # Adjust start position if not including markers
    if not include_markers:
        content_start = start_pos + len(start_marker)
    else:
        content_start = start_pos

    content = full_text[content_start:end_pos]

    return content, start_pos, end_pos


def extract_by_line_numbers(
    full_text: str,
    start_line: int,
    end_line: int
) -> Tuple[str, int]:
    """
    Extract content between line numbers (zero-indexed).

    This is the preferred extraction method as it eliminates marker ambiguity.
    Line numbers are precise and unique, preventing extraction of wrong sections.

    Args:
        full_text: Complete document text
        start_line: Starting line number (0-indexed, inclusive)
        end_line: Ending line number (0-indexed, exclusive)

    Returns:
        Tuple of (extracted_content, actual_token_count)

    Example:
        # Extract lines 10-20 (lines 10-19 inclusive)
        content, tokens = extract_by_line_numbers(text, 10, 20)
    """
    lines = full_text.split('\n')

    # Validate line numbers
    total_lines = len(lines)
    if start_line < 0:
        raise ValueError(f"start_line must be >= 0, got {start_line}")
    if end_line > total_lines:
        raise ValueError(f"end_line {end_line} exceeds document length {total_lines}")
    if start_line >= end_line:
        raise ValueError(f"start_line {start_line} must be < end_line {end_line}")

    # Extract lines
    content_lines = lines[start_line:end_line]
    content = '\n'.join(content_lines)

    # Calculate tokens
    tokens = estimate_tokens(content)

    return content, tokens


def find_line_number_for_pattern(text: str, pattern: str, is_regex: bool = False) -> Optional[int]:
    """
    Find the line number where a pattern first appears.

    Args:
        text: Text to search
        pattern: Pattern to find (string or regex)
        is_regex: Whether pattern is a regular expression

    Returns:
        Line number (0-indexed) or None if not found

    Example:
        line_num = find_line_number_for_pattern(text, "^TÍTULO II", is_regex=True)
        # Returns: 249 (line 250 in 1-indexed editors)
    """
    occurrences = find_all_occurrences(text, pattern, is_regex)
    if occurrences:
        # Return 0-indexed line number (editors use 1-indexed)
        return occurrences[0]['line_number'] - 1
    return None


def find_all_occurrences(text: str, pattern: str, is_regex: bool = False) -> List[Dict[str, any]]:
    """
    Find all occurrences of a pattern in text.

    Args:
        text: Text to search
        pattern: Pattern to find (string or regex)
        is_regex: Whether pattern is a regular expression

    Returns:
        List of dictionaries with 'match', 'position', 'line_number'
    """
    occurrences = []

    if is_regex:
        regex = re.compile(pattern, re.MULTILINE)
        for match in regex.finditer(text):
            line_num = text[:match.start()].count('\n') + 1
            occurrences.append({
                'match': match.group(),
                'position': match.start(),
                'line_number': line_num,
                'groups': match.groups() if match.groups() else None
            })
    else:
        # Simple string search
        pos = 0
        while True:
            pos = text.find(pattern, pos)
            if pos == -1:
                break
            line_num = text[:pos].count('\n') + 1
            occurrences.append({
                'match': pattern,
                'position': pos,
                'line_number': line_num
            })
            pos += len(pattern)

    return occurrences


def create_analysis_workspace(kb_name: str, output_dir: str = None) -> Path:
    """
    Create workspace directory for analysis process.

    Args:
        kb_name: Name of the knowledge base
        output_dir: Base output directory (default: .claude/skills/)

    Returns:
        Path to analysis workspace
    """
    if output_dir is None:
        if Path('.claude/skills').exists():
            output_dir = '.claude/skills'
        else:
            output_dir = str(Path.home() / '.claude' / 'skills')

    workspace = Path(output_dir) / f'{kb_name}_analysis'
    workspace.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (workspace / 'samples').mkdir(exist_ok=True)
    (workspace / 'responses').mkdir(exist_ok=True)

    return workspace


def save_analysis_request(workspace: Path, request_id: str, request_data: Dict) -> Path:
    """
    Save an analysis request for Claude Code to process.

    Args:
        workspace: Analysis workspace path
        request_id: Unique request identifier
        request_data: Request data dictionary

    Returns:
        Path to saved request file
    """
    request_file = workspace / 'requests' / f'{request_id}.json'
    request_file.parent.mkdir(exist_ok=True)

    with open(request_file, 'w', encoding='utf-8') as f:
        json.dump(request_data, f, indent=2, ensure_ascii=False)

    return request_file


def load_analysis_response(workspace: Path, request_id: str) -> Optional[Dict]:
    """
    Load analysis response from Claude Code.

    Args:
        workspace: Analysis workspace path
        request_id: Request identifier

    Returns:
        Response data dictionary or None if not found
    """
    response_file = workspace / 'responses' / f'{request_id}.json'

    if not response_file.exists():
        return None

    with open(response_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_structure(structure: Dict, output_path: Path) -> None:
    """
    Save document structure to JSON file.

    Args:
        structure: Structure dictionary
        output_path: Path to save structure.json
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(structure, f, indent=2, ensure_ascii=False)


def load_structure(structure_path: Path) -> Dict:
    """
    Load document structure from JSON file.

    Args:
        structure_path: Path to structure.json

    Returns:
        Structure dictionary
    """
    with open(structure_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_structure(structure: Dict, full_text: str) -> List[str]:
    """
    Validate that structure completely covers the document with no gaps or overlaps.

    Args:
        structure: Structure dictionary with hierarchy
        full_text: Complete document text

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Check required fields
    if 'hierarchy' not in structure:
        errors.append("Missing 'hierarchy' field in structure")
        return errors

    # Collect all sections and their positions
    sections = []

    def collect_sections(node, path=""):
        section_path = f"{path}/{node['title']}" if path else node['title']

        if 'start_marker' in node:
            pos = full_text.find(node['start_marker'])
            if pos == -1:
                errors.append(f"Start marker not found for section: {section_path}")
            else:
                sections.append({
                    'path': section_path,
                    'start': pos,
                    'marker': node['start_marker'][:50]
                })

        for child in node.get('children', []):
            collect_sections(child, section_path)

    for root_section in structure['hierarchy']:
        collect_sections(root_section)

    # Sort sections by start position
    sections.sort(key=lambda x: x['start'])

    # Check for overlaps
    for i in range(len(sections) - 1):
        current_end = sections[i]['start'] + 100  # Assume at least 100 chars per section
        next_start = sections[i + 1]['start']

        if current_end > next_start:
            errors.append(
                f"Possible overlap between '{sections[i]['path']}' and '{sections[i+1]['path']}'"
            )

    # Check coverage (at least some sections found)
    if not sections:
        errors.append("No sections found in structure")

    return errors


def generate_section_id(title: str, parent_id: Optional[str] = None, index: int = 0) -> str:
    """
    Generate a unique section ID.

    Args:
        title: Section title
        parent_id: Parent section ID (if any)
        index: Index within parent's children

    Returns:
        Unique section ID
    """
    if parent_id:
        return f"{parent_id}_{index:03d}"
    else:
        return f"section_{index:03d}"


def create_structure_template() -> Dict:
    """
    Create an empty structure template.

    Returns:
        Empty structure dictionary
    """
    return {
        'document_type': 'general',
        'language': 'unknown',
        'hierarchy': [],
        'metadata': {
            'total_sections': 0,
            'max_depth': 0,
            'analysis_date': '',
            'analyzer_notes': ''
        }
    }


def create_section_template(
    section_id: str,
    title: str,
    level: int,
    semantic_type: str = 'section',
    start_marker: str = '',
    end_marker: str = '',
    estimated_tokens: int = 0
) -> Dict:
    """
    Create a section dictionary template.

    Args:
        section_id: Unique section identifier
        title: Section title
        level: Hierarchical level (0=root, 1=major, 2=sub, etc.)
        semantic_type: Type of section (chapter, article, procedure, etc.)
        start_marker: Text marking section start
        end_marker: Text marking section end
        estimated_tokens: Approximate token count

    Returns:
        Section dictionary
    """
    return {
        'id': section_id,
        'title': title,
        'level': level,
        'semantic_type': semantic_type,
        'start_marker': start_marker,
        'end_marker': end_marker,
        'estimated_tokens': estimated_tokens,
        'children': []
    }


if __name__ == '__main__':
    # Test functions
    sample_text = """
    TITLE I - INTRODUCTION

    This is the introduction section.

    CHAPTER 1 - Getting Started

    Content of chapter 1.

    CHAPTER 2 - Advanced Topics

    Content of chapter 2.
    """

    # Test sample extraction
    samples = extract_document_sample(sample_text, sample_size=50)
    print("Samples extracted:", list(samples.keys()))

    # Test pattern finding
    chapters = find_all_occurrences(sample_text, r'^CHAPTER \d+', is_regex=True)
    print(f"Found {len(chapters)} chapters")

    # Test section extraction
    content, start, end = extract_section_content(
        sample_text,
        'CHAPTER 1',
        'CHAPTER 2'
    )
    print(f"Extracted section ({estimate_tokens(content)} tokens)")

    print("\nHelper functions ready for use!")
