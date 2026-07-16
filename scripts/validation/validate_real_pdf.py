#!/usr/bin/env python3
"""
Real PDF Validation for DBMA SPRINT15 / 3-E #7
Uses ONE real PDF from data/RAW to validate the complete pipeline.

This validation tests:
1. build_document_metadata() output 
2. process_one_file() execution
3. generated markdown frontmatter fields

The test uses a single PDF file with actual metadata to verify the pipeline works correctly.
"""

import os
import sys
import tempfile
from pathlib import Path

# Activate the correct environment and add to path
sys.path.insert(0, str(Path(__file__).parent))

from core.processing import build_converter, build_splitter, process_one_file
from core.document_identity import build_document_metadata
from core.extractors import extract_text_from_file
from core.utils import calculate_noise_score

def validate_real_pdf():
    """Execute controlled validation using real PDF from data directory"""
    
    print("=== DBMA Real PDF Controlled Validation ===")
    print("Testing: build_document_metadata() -> process_one_file() -> save_md_with_language()")
    print()
    
    # Use one of the existing PDF files
    pdf_files = list(Path("data").rglob("*.pdf"))
    if not pdf_files:
        print("ERROR: No PDF files found in data directory")
        return False
        
    # Select first PDF file
    test_pdf_path = pdf_files[0]
    print(f"Using real PDF input: {test_pdf_path.name}")
    print(f"Full path: {test_pdf_path}")
    print()
    
    # Create temporary output directory
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "output"
        output_dir.mkdir()
        
        # Step 1: Extract text from PDF (this is part of process_one_file)
        print("Step 1: Extracting text from PDF...")
        converter = build_converter()
        splitter = build_splitter(1200, 120)
        
        file_info = {
            "path": str(test_pdf_path),
            "name": test_pdf_path.name,
            "ext": ".pdf"
        }
        
        try:
            raw_result = extract_text_from_file(str(test_pdf_path), converter=converter, use_ocr=False)
            full_text = raw_result.get("text", "") or ""
            print(f"✓ Text extracted successfully: {len(full_text)} characters")
            
            # Step 2: Calculate noise score
            print("Step 2: Calculating noise score...")
            noise = calculate_noise_score(full_text, file_type="pdf", is_ocr=False)
            print(f"✓ Noise score calculated: {noise['score']}")
            
            # Step 3: Build document metadata (this is the key function we're testing)
            print("Step 3: Building document metadata...")
            document_meta = build_document_metadata(
                content=full_text,
                source_file=test_pdf_path.name,
                language="en",  # This will be detected in process_one_file
                noise_score=noise["score"],
                noise_mode=noise.get("mode", "-"),
                source_type="pdf",
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
            
            # Step 4: Process file using process_one_file (this will call save_md_with_language internally)
            print("Step 4: Processing file through process_one_file...")
            result = process_one_file(
                file_info=file_info,
                converter=converter,
                splitter=splitter,
                output_dir=str(output_dir),
                chunk_size=1200,
                chunk_overlap=120
            )
            
            print(f"✓ File processing completed: success={result['success']}")
            
            if not result["success"]:
                print("  WARNING: Processing failed - checking logs for details")
                for log in result.get("logs", []):
                    print(f"    {log.get('msg', '')}")
            
            # Step 5: Locate the generated markdown file
            print("Step 5: Locating generated markdown file...")
            md_files = list(output_dir.glob("*.md"))
            if not md_files:
                print("  ERROR: No markdown file found!")
                return False
                
            md_file = md_files[0]
            print(f"✓ Generated markdown file: {md_file.name}")
            
            # Step 6: Parse and validate frontmatter
            print("Step 6: Parsing frontmatter...")
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Extract frontmatter (lines between ---)
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
            
            # Step 7: Report results
            print("\n=== VALIDATION RESULTS ===")
            print(f"Input PDF: {test_pdf_path.name}")
            print(f"Generated Markdown: {md_file.name}")
            print(f"PDF metadata detected:")
            for key in ['title', 'author', 'chapter', 'page']:
                if key in document_meta and document_meta[key] is not None:
                    print(f"  {key}: {document_meta[key]}")
                else:
                    print(f"  {key}: NOT FOUND (from document_metadata)")
            
            print(f"Generated markdown frontmatter fields:")
            for key in ['title', 'author', 'chapter', 'page']:
                if key in frontmatter:
                    print(f"  {key}: {frontmatter[key]}")
                else:
                    print(f"  {key}: NOT FOUND (from frontmatter)")
            
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
                
        except Exception as e:
            print(f"ERROR during validation: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = validate_real_pdf()
    sys.exit(0 if success else 1)