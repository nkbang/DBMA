# DBMA v1.1.0 — Operations Manual

---

## System Overview

DBMA is a research engine for Korean theological corpus analysis. This manual covers operational procedures for maintaining and operating DBMA in production.

---

## Storage Layout

```
DBMA/
├── data/
│   ├── RAW/                    # Input documents (place PDFs here)
│   └── 제련완성본/              # Processed output corpus
├── chroma_db/                  # Vector database (auto-created on first run)
├── core/identity_registry.json # Document identity registry
├── logs/                       # Runtime logs
├── output/                     # Audit reports and benchmark outputs
├── config.yaml                 # Main configuration
└── ui/app.py                   # Application entry point
```

### Storage Size Estimates

| Component | Typical Size | Grows With |
|-----------|-------------|------------|
| chroma_db/ | 500 MB - 2 GB | Corpus size |
| data/RAW/ | Variable | Number of PDFs |
| data/제련완성본/ | 1-3 GB | Processed documents |
| core/identity_registry.json | <1 MB | Document count |
| logs/ | <100 MB/day | Runtime duration |

---

## Backup Procedure

### Full System Backup

```bash
# Navigate to parent directory
cd ~/DBMA

# Create backup archive
tar czf dbma-backup-$(date +%Y%m%d).tar.gz \
    chroma_db/ \
    data/제련완성본/ \
    core/identity_registry.json \
    config.yaml
```

### Corpus-Only Backup

```bash
# Just the processed corpus (most important)
tar czf dbma-corpus-backup-$(date +%Y%m%d).tar.gz \
    data/제련완성본/
```

### ChromaDB-Only Backup

```bash
# Vector index backup (fast, no reprocessing needed)
tar czf dbma-vector-backup-$(date +%Y%m%d).tar.gz chroma_db/
```

### Automated Daily Backup (Optional)

```bash
#!/bin/bash
# save as ~/DBMA/scripts/backup.sh
BACKUP_DIR=/path/to/backup/location
DATE=$(date +%Y%m%d)
cd ~/DBMA
tar czf ${BACKUP_DIR}/dbma-backup-${DATE}.tar.gz \
    chroma_db/ \
    data/제련완성본/ \
    core/identity_registry.json \
    config.yaml
# Keep only last 7 days
find ${BACKUP_DIR} -name "dbma-backup-*.tar.gz" -mtime +7 -delete
```

Make executable: `chmod +x ~/DBMA/scripts/backup.sh`

---

## Restore Procedure

### Full Restore

```bash
# Navigate to parent directory
cd ~

# Extract backup (replace with your backup filename)
tar xzf /path/to/dbma-backup-YYYYMMDD.tar.gz -C ~/DBMA/

# Verify restore
ls ~/DBMA/chroma_db/
ls ~/DBMA/data/제련완성본/
```

### Corpus Restore Only

```bash
tar xzf /path/to/dbma-corpus-backup-YYYYMMDD.tar.gz -C ~/DBMA/
```

### Vector Index Restore Only

```bash
tar xzf /path/to/dbma-vector-backup-YYYYMMDD.tar.gz -C ~/DBMA/
# No restart needed — ChromaDB uses restored index immediately
```

---

## Upgrade Procedure

### Version Upgrade (v1.0 → v1.x)

```bash
# 1. Backup current installation
cd ~/DBMA
tar czf dbma-pre-upgrade-$(date +%Y%m%d).tar.gz \
    chroma_db/ \
    data/제련완성본/ \
    core/identity_registry.json \
    config.yaml

# 2. Pull new version
git pull origin main

# 3. Check for dependency changes
cat requirements.txt | diff -u <(pip freeze) -

# 4. Update dependencies if needed
pip install -r requirements.txt

# 5. Verify core modules load
python -c "from core.config import DEFAULT_CHUNK_SIZE; print('OK')"
python -c "from core.retrieval import HybridRetrieval; print('OK')"

# 6. Restart DBMA
streamlit run ui/app.py
```

### Configuration Migration

If config.yaml structure changed between versions:

1. Compare old vs new config.yaml
2. Copy custom values from backup
3. Update new config.yaml accordingly
4. Test with `python -c "from core.config import load_config; print(load_config())"`

---

## Monitoring

### Health Checks

| Check | Command | Expected |
|-------|---------|----------|
| Corpus exists | `ls data/제련완성본/ | wc -l` | >0 |
| ChromaDB initialized | `ls chroma_db/` | non-empty |
| Identity registry | `cat core/identity_registry.json \| jq .` | valid JSON |
| Core modules load | `python -c "import core.retrieval"` | no error |

### Log Review

```bash
# Recent errors
grep -i ERROR logs/dbma.log | tail -20

# Search for specific module errors
grep -i "chroma" logs/dbma.log

# Memory usage trend (if logged)
grep -i "memory" logs/dbma.log
```

### Performance Monitoring

| Metric | Check Method | Threshold |
|--------|-------------|-----------|
| Query latency | UI Research page timing | <5 seconds |
| Corpus size | `du -sh data/제련완성본/` | track over time |
| ChromaDB size | `du -sh chroma_db/` | <10 GB |
| Disk usage | `df -h ~` | >20% free |

---

## Troubleshooting

### "ChromaDB not found" or initialization error

```bash
# Remove and let DBMA auto-recreate
rm -rf chroma_db/
streamlit run ui/app.py
```

### Corpus not loading

```bash
# Verify corpus exists
ls data/제련완성본/

# If missing, check RAW documents
ls data/RAW/

# Re-process from RAW via UI Processing page
```

### Search returning empty results

```bash
# Check ChromaDB collections
python -c "
import chromadb
client = chromadb.PersistentClient(path='chroma_db')
print('Collections:', client.list_collections())
"
```

### High memory usage

```bash
# Reduce chunk_size in config.yaml (from 512 to 256)
# Restart DBMA after change
```

---

## Maintenance Schedule

| Task | Frequency | Command/Method |
|------|-----------|---------------|
| Backup corpus | Weekly | Manual or automated script |
| Review logs | Monthly | `grep -i ERROR logs/dbma.log` |
| Check disk space | Monthly | `df -h ~` |
| Dependency updates | Quarterly | `pip install -r requirements.txt` |
| Config review | Per version upgrade | Compare config.yaml diffs |

---

## Contact and Support

- Repository: http://100.94.139.122:3000/David/DBMA.git
- GitHub: https://github.com/nkbang/DBMA.git
- Version: v1.1.0 (Release Baseline)

---

*DBMA v1.1.0 is production-grade. Follow backup procedures before any major changes.*