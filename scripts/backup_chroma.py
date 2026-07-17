#!/usr/bin/env python3
"""
ChromaDB Backup Script
Creates timestamped backups of ChromaDB collection without modifying the original database.
"""

import os
import shutil
import time
import logging
from pathlib import Path
from datetime import datetime
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup_chroma.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# [SPRINT20-I-D-5] dbma.py archived to archive/legacy/. ChromaDB is a legacy
# store (dbma-only, ADR-003 KEEP); its path is the project-root "chroma_db"
# directory — declared here explicitly instead of importing the archived module.
LEGACY_CHROMA_DIR = Path("chroma_db")


def get_chroma_db_path():
    """Get the ChromaDB path (legacy store, project-root chroma_db/)."""
    return LEGACY_CHROMA_DIR

def create_backup_directory():
    """Create backup directory with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path("backups") / f"chroma_backup_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created backup directory: {backup_dir}")
    return backup_dir

def backup_chroma_db(source_path, backup_path):
    """Create a backup of the ChromaDB collection."""
    try:
        # Check if source exists
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Source directory does not exist: {source_path}")
        
        # Create backup
        logger.info(f"Starting backup from {source_path} to {backup_path}")
        
        # Copy the entire chroma_db directory
        shutil.copytree(source_path, backup_path, dirs_exist_ok=True)
        
        logger.info("Backup completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return False

def verify_backup_integrity(backup_path):
    """Verify the integrity of the backup."""
    try:
        # Check if backup directory exists
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup directory does not exist: {backup_path}")
        
        # Check for required files
        required_files = ['chroma.sqlite3']
        backup_files = list(backup_path.rglob('*'))
        backup_file_names = [f.name for f in backup_files if f.is_file()]
        
        logger.info(f"Verifying backup integrity...")
        logger.info(f"Backup contains {len(backup_files)} items")
        
        # Simple verification - check if the main database file exists
        if 'chroma.sqlite3' not in backup_file_names:
            raise FileNotFoundError("Required chroma.sqlite3 file not found in backup")
            
        logger.info("Backup integrity verification passed")
        return True
        
    except Exception as e:
        logger.error(f"Backup integrity verification failed: {e}")
        return False

def main():
    """Main backup function."""
    parser = argparse.ArgumentParser(description='Backup ChromaDB collection')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without actually doing it')
    args = parser.parse_args()
    
    logger.info("Starting ChromaDB backup process")
    
    # Get paths
    source_path = get_chroma_db_path()
    backup_dir = create_backup_directory()
    backup_path = backup_dir / "chroma_db"
    
    logger.info(f"Source path: {source_path}")
    logger.info(f"Backup path: {backup_path}")
    
    if args.dry_run:
        logger.info("Dry run mode - would backup from source to backup directory")
        return True
    
    # Perform backup
    success = backup_chroma_db(source_path, backup_path)
    
    if success:
        # Verify backup
        integrity_ok = verify_backup_integrity(backup_path)
        
        if integrity_ok:
            logger.info("Backup and verification completed successfully")
            print(f"Backup created at: {backup_path}")
            return True
        else:
            logger.error("Backup verification failed")
            return False
    else:
        logger.error("Backup process failed")
        return False

if __name__ == "__main__":
    main()