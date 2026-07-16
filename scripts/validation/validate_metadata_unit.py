#!/usr/bin/env python3
"""
Simple Controlled Validation for DBMA SPRINT15 / 3-E #7
Validates the document metadata processing pipeline by testing functions directly.
"""

import os
import sys
import tempfile
from pathlib import Path

# Activate the correct environment and add to path
sys.path.insert(0, str(Path(__file__).parent))

from core.document_identity import build_document_metadata
from core.processing import save_md_with_language
from core.utils import calculate_noise_score

def validate_functions():
    """Execute controlled validation of document metadata functions"""
    
    print("=== DBMA Controlled Validation (Simple) ===")
    print("Testing: build_document_metadata() -> save_md_with_language()")
    print()
    
    # Test data - use sample text content
    sample_text = """
    This is a test document for validating the document metadata pipeline.
    
    The document contains multiple sections and paragraphs. It demonstrates 
    how the system processes text content to generate proper metadata and 
    markdown frontmatter.
    
    Section 1: Introduction
    This section provides an overview of the document's purpose and scope.
    
    Section 2: Main Content  
    This is where the primary information and arguments are presented.
    
    Section 3: Conclusion
    The document concludes with key findings and recommendations.
    """
    
    print("Using sample text input")
    print(f"Text length: {len(sample_text)} characters")
    print()
    
    # Step 1: Calculate noise score (this is part of the process)
    print("Step 1: Calculating noise score...")
    noise = calculate_noise_score(sample_text, file_type="txt", is_ocr=False)
    print(f"✓ Noise score calculated: {noise['score']}")
    print()
    
    # Step 2: Build document metadata (this is the key function we're testing)
    print("Step 2: Building document metadata...")
    document_meta = build_document_metadata(
        content=sample_text,
        source_file="test_document.txt",
        language="en",
        noise_score=noise["score"],
        noise_mode=noise.get("mode", "-"),
        source_type="txt",
        is_ocr=False,
        chunk_count=0  # We don't have chunks yet
    )
    print("✓ Document metadata built successfully")
    
    # Print the metadata fields for verification
    print("\nGenerated Document Metadata:")
    print("-" * 40)
    for key, value in document_meta.items():
        print(f"{key}: {value}")
    print("-" * 40)
    print()
    
    # Step 3: Test save_md_with_language function (this is the final step in the pipeline)
    print("Step 3: Testing save_md_with_language function...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "output"
        output_dir.mkdir()
        
        # Call save_md_with_language directly
        md_path = save_md_with_language(
            output_dir=str(output_dir),
            stem="test_document",
            source_name="test_document.txt",
            text=sample_text,
            noise=noise,
            source_type="txt",
            language="en",
            document_meta=document_meta
        )
        
        print(f"✓ Markdown file created: {md_path}")
        
        # Read and parse the generated markdown to check frontmatter
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        print("\nGenerated Markdown Content:")
        print("-" * 40)
        print(content[:500] + "..." if len(content) > 500 else content)
        print("-" * 40)
        
        # Extract and analyze frontmatter
        lines = content.split('\n')
        frontmatter_lines = []
        in_frontmatter = False
        
        for line in lines:
            if line.strip() == '---':
                if not in_frontmatter:
                    in_frontmatter = True
                else:
                    in_frontmatter = False
                    break
            elif in_frontmatter:
                frontmatter_lines.append(line)
        
        # Parse frontmatter key-value pairs
        frontmatter = {}
        for line in frontmatter_lines:
            if ':' in line:
                key, value = line.split(':', 1)
                frontmatter[key.strip()] = value.strip()
        
        print("\nGenerated Frontmatter Fields:")
        print("-" * 40)
        for key, value in frontmatter.items():
            print(f"{key}: {value}")
        print("-" * 40)
        
        # Validate required fields
        required_fields = ['title', 'author', 'chapter', 'page']
        missing_fields = []
        present_fields = []
        
        for field in required_fields:
            if field in frontmatter:
                present_fields.append(field)
            else:
                missing_fields.append(field)
        
        print(f"\nRequired Fields Analysis:")
        print(f"✓ Present: {present_fields}")
        if missing_fields:
            print(f"✗ Missing: {missing_fields}")
        else:
            print("✓ All required fields present")
        
        # Step 4: Report results
        print("\n=== VALIDATION RESULTS ===")
        print(f"1. Input Text: Sample text (test content)")
        print(f"2. Generated Markdown: test_document.md")
        print(f"3. Frontmatter Fields:")
        for key in ['title', 'author', 'chapter', 'page']:
            if key in frontmatter:
                print(f"   {key}: {frontmatter[key]}")
            else:
                print(f"   {key}: NOT FOUND")
        
        # Determine pass/fail
        all_required_present = len(missing_fields) == 0
        
        if all_required_present:
            print("\n✅ VALIDATION PASSED")
            print("All required frontmatter fields found in generated markdown.")
            return True
        else:
            print(f"\n❌ VALIDATION FAILED")
            print(f"Missing required fields: {missing_fields}")
            return False

if __name__ == "__main__":
    success = validate_functions()
    sys.exit(0 if success else 1)