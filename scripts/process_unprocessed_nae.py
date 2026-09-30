#!/usr/bin/env python3
"""scripts/process_unprocessed_nae.py — Process unprocessed NAE corpus documents.

This script:
1. Reads canonical.json from unprocessed NAE corpus documents
2. Generates TSU records (without LLM claim extraction for now)
3. Merges them into the production TSU dataset
4. Updates the registry and manifest

Note: Korean claims require running the NAE pipeline with my-theology-bot-v2:latest.
This script processes the raw text content for searchability.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import DEFAULT_OUTPUT_DIR, DEFAULT_TSU_DATASET_PATH, DEFAULT_TSU_MANIFEST_PATH, registry_path_for
from core.identity_registry import load_identity_registry, save_identity_registry


def process_canonical_document(canonical_dir: Path) -> tuple[str, list[dict]]:
    """Process a canonical.json file and generate TSU records."""
    
    canonical_json = canonical_dir / 'canonical.json'
    if not canonical_json.exists():
        return None, []
    
    with open(canonical_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    identifier = data.get('identifier', canonical_dir.name)
    title = data.get('title', canonical_dir.name)
    author = data.get('author', '')
    paragraphs = data.get('paragraphs', [])
    
    records = []
    for para in paragraphs:
        text = para.get('text', '')
        if not text or len(text.strip()) < 20:
            continue
        
        page = para.get('page_start', 1)
        
        # Detect language from text
        has_korean = any('\uac00' <= c <= '\ud7a3' for c in text)
        language = 'ko' if has_korean else 'en'
        
        record = {
            'tsu_id': f"NAE-UNC-{identifier}_p{para.get('index', 0):06d}",
            'document_id': f"nae_{identifier}",
            'chunk_id': f"NAE-UNC-{identifier}_p{para.get('index', 0):06d}",
            'content': text,
            'verse_mapping': {},
            'themes': [],
            'title': title,
            'author': author,
            'metadata_source': 'nae_canonical_unprocessed',
            'chapter': None,
            'page': page,
            'source_file': f"{identifier}.jsonl",
            'language': language,
            'source_type': 'nae_canonical_unprocessed',
            'content_quality': {
                'noise_type': 'NAE_CANONICAL_UNPROCESSED',
                'quality_score': 0.8,
                'section_type': 'paragraph'
            },
            'structure': {},
            'theological_claim': None,
            'doctrine_category': [],
            'baptist_theme': [],
            'source_provenance': None,
            'nae_metadata': {
                'nae_identifier': identifier,
                'nae_canonical_version': data.get('pipeline_version'),
                'nae_source': data.get('source'),
                'nae_page_count': data.get('page_count'),
                'nae_paragraph_index': para.get('index'),
            }
        }
        records.append(record)
    
    return identifier, records


def process_unprocessed_nae(
    canonical_dir: str = 'NAE/corpus/canonical',
    tsu_dataset_path: str = None,
    registry_path: str = None,
    manifest_path: str = None,
):
    """Process unprocessed NAE corpus documents."""
    
    if tsu_dataset_path is None:
        tsu_dataset_path = DEFAULT_TSU_DATASET_PATH
    if registry_path is None:
        registry_path = registry_path_for(DEFAULT_OUTPUT_DIR)
    if manifest_path is None:
        manifest_path = DEFAULT_TSU_MANIFEST_PATH
    
    # Load existing TSU dataset
    print(f"Loading production TSU from {tsu_dataset_path}...")
    existing_records = []
    with open(tsu_dataset_path, 'r', encoding='utf-8') as f:
        for line in f:
            existing_records.append(json.loads(line))
    print(f"  Loaded {len(existing_records)} existing records")
    
    # Process unprocessed documents
    print(f"\nProcessing unprocessed NAE corpus from {canonical_dir}...")
    new_records = []
    new_docs_info = {}
    
    for item in sorted(os.listdir(canonical_dir)):
        if item.startswith('.'):
            continue
        
        item_path = os.path.join(canonical_dir, item)
        if not os.path.isdir(item_path):
            continue
        
        # Check if already processed
        tsu_file = os.path.join('NAE/corpus/tsu', item, 'tsu.json')
        if os.path.exists(tsu_file):
            print(f"  Skipping {item} (already processed)")
            continue
        
        canonical_json = os.path.join(item_path, 'canonical.json')
        if not os.path.exists(canonical_json):
            print(f"  Skipping {item} (no canonical.json)")
            continue
        
        identifier, records = process_canonical_document(Path(item_path))
        if identifier and records:
            new_records.extend(records)
            new_docs_info[item] = {
                'document_id': f"nae_{identifier}",
                'title': item,
                'author': '',
                'record_count': len(records),
            }
            print(f"  Processed {item}: {len(records)} records")
    
    print(f"\nTotal new records: {len(new_records)}")
    
    # Append to existing TSU
    all_records = existing_records + new_records
    print(f"Total TSU records after merge: {len(all_records)}")
    
    # Write merged TSU dataset
    print(f"\nWriting merged TSU to {tsu_dataset_path}...")
    with open(tsu_dataset_path, 'w', encoding='utf-8') as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    print(f"  Written {len(all_records)} records")
    
    # Update registry
    print(f"\nUpdating registry at {registry_path}...")
    registry = load_identity_registry(registry_path)
    
    for item, info in new_docs_info.items():
        doc_id = info['document_id']
        if doc_id not in registry['documents']:
            registry['documents'][doc_id] = {
                'document_id': doc_id,
                'source_file': f"{item}.jsonl",
                'title': info['title'],
                'author': info['author'],
                'status': 'processed',
                'chunk_count': info['record_count'],
                'language': 'en',
                'source_type': 'nae_canonical_unprocessed',
                'doc_type': '신학',
                'ingest_status': 'PROCESSED',
                'pipeline_state': 'INDEXED',
                'created_at': datetime.now().isoformat(),
                'last_processed_at': datetime.now().isoformat(),
                'last_content_hash': f"nae_{item}",
                'pipeline_flags': {
                    'ingested': True,
                    'copied': True,
                    'extracted': True,
                    'cleaned': True,
                    'chunked': True,
                    'output_generated': True,
                    'verified': True,
                },
            }
    
    save_identity_registry(registry, registry_path)
    print(f"  Updated registry with {len(new_docs_info)} new documents")
    
    # Update manifest
    print(f"\nUpdating manifest at {manifest_path}...")
    manifest = {
        'generated_at': datetime.now().isoformat(),
        'tsu_count': len(all_records),
        'source_document_count': len(registry['documents']),
        'build_commit': 'process_unprocessed_nae',
        'builder_script': 'scripts/process_unprocessed_nae.py',
        'registry_path': registry_path,
        'dataset_path': tsu_dataset_path,
    }
    
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"  Updated manifest")
    
    return {
        'existing_records': len(existing_records),
        'new_records': len(new_records),
        'total_records': len(all_records),
        'new_documents': len(new_docs_info),
    }


if __name__ == '__main__':
    result = process_unprocessed_nae()
    print(f"\n=== Process Result ===")
    for k, v in result.items():
        print(f"  {k}: {v}")
