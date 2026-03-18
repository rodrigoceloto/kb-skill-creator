#!/bin/bash

# Example: Creating a knowledge base from multiple source files
# This demonstrates how to combine multiple documents into a single, unified knowledge base

echo "Testing Knowledge Base Generator with Multiple Sources"
echo "======================================================"
echo ""
echo "This test will create a knowledge base called 'example-product-docs'"
echo "combining two markdown files:"
echo "  1. sample-doc-1.md (Getting Started Guide)"
echo "  2. sample-doc-2.md (API Reference)"
echo ""

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KB_GENERATOR="$SCRIPT_DIR/../scripts/generate_kb.py"

# Check if the generator script exists
if [ ! -f "$KB_GENERATOR" ]; then
    echo "Error: Generator script not found at $KB_GENERATOR"
    exit 1
fi

# Check if sample docs exist
if [ ! -f "$SCRIPT_DIR/sample-doc-1.md" ] || [ ! -f "$SCRIPT_DIR/sample-doc-2.md" ]; then
    echo "Error: Sample documents not found"
    exit 1
fi

echo "Running generator..."
echo ""

# Run the generator with multiple sources
python3 "$KB_GENERATOR" \
  --name "example-product-docs" \
  --sources "$SCRIPT_DIR/sample-doc-1.md" "$SCRIPT_DIR/sample-doc-2.md" \
  --description "Example product documentation combining getting started guide and API reference"

if [ $? -eq 0 ]; then
    echo ""
    echo "======================================================"
    echo "Success! Knowledge base created."
    echo ""
    echo "The skill 'example-product-docs' is now available at:"
    echo "  .claude/skills/example-product-docs/"
    echo ""
    echo "Contents:"
    echo "  - SKILL.md: Main skill file (auto-discovered by Claude)"
    echo "  - index.md: Hierarchical navigation index"
    echo "  - metadata.json: Technical metadata"
    echo "  - chunks/: Individual section files"
    echo ""
    echo "Try asking Claude questions like:"
    echo "  - 'How do I install the product?'"
    echo "  - 'What are the API authentication methods?'"
    echo "  - 'Show me the users endpoint documentation'"
    echo ""
    echo "Claude will automatically discover and use this skill!"
else
    echo ""
    echo "Error: Knowledge base generation failed"
    exit 1
fi
