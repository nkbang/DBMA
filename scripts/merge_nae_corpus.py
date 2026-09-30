#!/usr/bin/env python3
"""scripts/merge_nae_corpus.py — Merge NAE corpus TSU into production TSU.

This script:
1. Reads all NAE corpus TSU records from NAE/corpus/tsu/*/tsu.json
2. Transforms them to production TSU format
3. Appends them to the production TSU dataset
4. Updates the registry with NAE corpus documents
5. Updates the manifest
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import DEFAULT_OUTPUT_DIR, DEFAULT_TSU_DATASET_PATH, DEFAULT_TSU_MANIFEST_PATH, registry_path_for
from core.identity_registry import load_identity_registry, save_identity_registry


def transform_nae_record(nae_rec: dict, doc_id: str) -> dict:
    """Transform a NAE corpus TSU record to production TSU format."""
    
    # Detect language from claim text
    claim = nae_rec.get('claim', '')
    has_korean = any('\uac00' <= c <= '\ud7a3' for c in claim)
    language = 'ko' if has_korean else 'en'
    
    # Map doctrine to doctrine_category
    doctrine = nae_rec.get('doctrine', '')
    doctrine_category = [doctrine] if doctrine else []
    
    # Detect baptist themes from doctrine
    baptist_themes = []
    if doctrine:
        doc_lower = doctrine.lower()
        if 'soteriology' in doc_lower:
            baptist_themes.append('soteriology')
        elif 'ecclesiology' in doc_lower:
            baptist_themes.append('ecclesiology')
        elif 'pneumatology' in doc_lower:
            baptist_themes.append('pneumatology')
        elif 'christology' in doc_lower:
            baptist_themes.append('christology')
        elif 'trinitarian' in doc_lower or 'trinity' in doc_lower:
            baptist_themes.append('trinitarian_doctrine')
        elif 'baptism' in doc_lower:
            baptist_themes.append('baptism')
        elif 'covenant' in doc_lower:
            baptist_themes.append('covenant_theology')
        elif 'eschatology' in doc_lower:
            baptist_themes.append('eschatology')
        elif 'hermeneutics' in doc_lower or 'exegesis' in doc_lower:
            baptist_themes.append('biblical_hermeneutics')
    
    return {
        # Production TSU required fields
        'tsu_id': f"NAE-{nae_rec['id']}",
        'document_id': doc_id,
        'chunk_id': f"NAE-{nae_rec['id']}",
        'content': nae_rec.get('source_text', ''),
        'verse_mapping': {},
        'themes': [],
        'title': nae_rec.get('book', ''),
        'author': nae_rec.get('author', ''),
        'metadata_source': 'nae_canonical',
        'chapter': None,
        'page': nae_rec.get('page'),
        'source_file': f"{nae_rec.get('identifier', '')}.jsonl",
        'language': language,
        'source_type': 'nae_canonical',
        'content_quality': {
            'noise_type': 'NAE_CANONICAL',
            'quality_score': 1.0,
            'section_type': 'claim'
        },
        'structure': {},
        # Theological fields
        'theological_claim': claim,
        'doctrine_category': doctrine_category,
        'baptist_theme': baptist_themes,
        'source_provenance': None,
        'nae_metadata': {
            'nae_id': nae_rec.get('id'),
            'nae_doctrine': doctrine,
            'nae_confidence': nae_rec.get('confidence'),
            'nae_extraction_method': nae_rec.get('extraction_method'),
            'nae_review_status': nae_rec.get('review_status'),
            'nae_canonical_version': nae_rec.get('canonical_version'),
        }
    }


def merge_nae_corpus(
    nae_corpus_dir: str = 'NAE/corpus/tsu',
    tsu_dataset_path: str = None,
    registry_path: str = None,
    manifest_path: str = None,
):
    """Merge NAE corpus TSU into production TSU dataset."""
    
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
    
    # Read NAE corpus TSU records
    print(f"\nReading NAE corpus from {nae_corpus_dir}...")
    nae_records = []
    nae_docs_info = {}
    
    for item in sorted(os.listdir(nae_corpus_dir)):
        item_path = os.path.join(nae_corpus_dir, item)
        if os.path.isdir(item_path):
            tsu_file = os.path.join(item_path, 'tsu.json')
            if os.path.exists(tsu_file):
                with open(tsu_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    doc_id = f"nae_{item}"
                    nae_docs_info[item] = {
                        'document_id': doc_id,
                        'title': data[0].get('book', ''),
                        'author': data[0].get('author', ''),
                        'record_count': len(data),
                    }
                    
                    # Transform and add records
                    for nae_rec in data:
                        prod_rec = transform_nae_record(nae_rec, doc_id)
                        nae_records.append(prod_rec)
    
    print(f"  Read {len(nae_records)} NAE corpus records from {len(nae_docs_info)} documents")
    
    # Append to existing TSU
    all_records = existing_records + nae_records
    print(f"\nTotal TSU records after merge: {len(all_records)}")
    
    # Write merged TSU dataset
    print(f"\nWriting merged TSU to {tsu_dataset_path}...")
    with open(tsu_dataset_path, 'w', encoding='utf-8') as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    print(f"  Written {len(all_records)} records")
    
    # Update registry
    print(f"\nUpdating registry at {registry_path}...")
    registry = load_identity_registry(registry_path)
    
    for item, info in nae_docs_info.items():
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
                'source_type': 'nae_canonical',
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
    print(f"  Updated registry with {len(nae_docs_info)} new documents")
    
    # Update manifest
    print(f"\nUpdating manifest at {manifest_path}...")
    manifest = {
        'generated_at': datetime.now().isoformat(),
        'tsu_count': len(all_records),
        'source_document_count': len(registry['documents']),
        'build_commit': 'merge_nae_corpus',
        'builder_script': 'scripts/merge_nae_corpus.py',
        'registry_path': registry_path,
        'dataset_path': tsu_dataset_path,
    }
    
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"  Updated manifest")
    
    return {
        'existing_records': len(existing_records),
        'nae_records': len(nae_records),
        'total_records': len(all_records),
        'new_documents': len(nae_docs_info),
    }


if __name__ == '__main__':
    result = merge_nae_corpus()
    print(f"\n=== Merge Result ===")
    for k, v in result.items():
        print(f"  {k}: {v}")
