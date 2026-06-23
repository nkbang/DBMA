from pathlib import Path

ROOT = Path('/Users/David/DBMA')
DOCS = ROOT / 'docs'

def main():
    (DOCS / 'STATE.md').write_text('...', encoding='utf-8')
    (DOCS / 'TODO.md').write_text('...', encoding='utf-8')
    (DOCS / 'PROCESS_LOG.md').write_text('...', encoding='utf-8')
    (DOCS / 'CHANGELOG.md').write_text('...', encoding='utf-8')

if __name__ == '__main__':
    main()
