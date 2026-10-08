#!/usr/bin/env bash
# clean_env_snapshot.sh — 깨끗한 환경 평가용 읽기 전용 스냅샷 수집기.
# 절차서: docs/GATE2_CLEAN_ENV_EVALUATION_PROCEDURE.md
#
# 사용: bash clean_env_snapshot.sh <label> [출력 디렉터리]
#   label 예: precheck, before, after-install, after-rerun
# 읽기 전용: 아무것도 설치·삭제·기동하지 않는다. 파일은 출력 디렉터리에만 쓴다.
# 출력 파일은 라벨별로 새 이름을 쓰며 기존 파일을 덮어쓰지 않는다(덮어쓰면 중단).
set -u
LABEL="${1:-}"
OUTDIR="${2:-$PWD/gate2-clean-env}"
if [ -z "$LABEL" ]; then echo "Usage: $0 <label> [outdir]" >&2; exit 2; fi
mkdir -p "$OUTDIR"
OUT="$OUTDIR/snapshot_${LABEL}.txt"
if [ -e "$OUT" ]; then echo "ERROR: $OUT already exists (덮어쓰지 않음)" >&2; exit 2; fi

sect() { printf '\n## %s\n' "$1"; }
present() { # 이름, 경로/명령
    if command -v "$2" >/dev/null 2>&1; then printf '%-22s PRESENT  %s\n' "$1" "$(command -v "$2")"
    else printf '%-22s absent\n' "$1"; fi
}
exists() { if [ -e "$2" ]; then printf '%-22s PRESENT  %s\n' "$1" "$2"; else printf '%-22s absent    %s\n' "$1" "$2"; fi; }

{
echo "# clean-env snapshot: ${LABEL}"
echo "recorded_at_utc: $(date -u +%FT%TZ)"
echo "recorded_at_local: $(date '+%F %T %z')"
sect "system"
echo "sw_vers: $(sw_vers -productVersion 2>/dev/null) ($(sw_vers -buildVersion 2>/dev/null))"
echo "arch: $(uname -m)    kernel: $(uname -r)"
echo "memory_gb: $(( $(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1024 / 1024 / 1024 ))"
echo "user: $(id -un)    home: $HOME"
echo "disk_free: $(df -h "$HOME" | awk 'NR==2 {print $4" free of "$2}')"
echo "virtual_machine: $(sysctl -n kern.hv_vmm_present 2>/dev/null || echo unknown)  (1이면 VM)"
sect "tools (깨끗한 환경이면 대부분 absent여야 함)"
present brew brew; present ollama ollama; present python3.11 python3.11
present pdftoppm pdftoppm; present tesseract tesseract
exists "Ollama.app" /Applications/Ollama.app
exists "ollama symlink" /usr/local/bin/ollama
exists "~/.ollama" "$HOME/.ollama"
exists "libhunspell link" /usr/local/lib/libhunspell.dylib
exists "hunspell include link" /usr/local/Cellar/hunspell/1.6.2/include/hunspell
exists "Command Line Tools" /Library/Developer/CommandLineTools
exists "~/내서재_베타" "$HOME/내서재_베타"
sect "installed version"
if [ -f "$HOME/내서재_베타/.installed_tag" ]; then echo "installed_tag: $(cat "$HOME/내서재_베타/.installed_tag")"; else echo "installed_tag: (none)"; fi
sect "brew packages (brew가 있을 때만)"
if command -v brew >/dev/null 2>&1; then
    for p in poppler tesseract python@3.11 hunspell ollama; do
        brew list "$p" >/dev/null 2>&1 && echo "brew:$p PRESENT" || echo "brew:$p absent"
    done
else echo "(brew 없음)"; fi
sect "ollama models (서버가 응답할 때만)"
if command -v ollama >/dev/null 2>&1 && ollama list >/dev/null 2>&1; then ollama list; else echo "(ollama 없음 또는 서버 미응답)"; fi
sect "listening ports (8520=앱, 11434=Ollama, 6333=Qdrant)"
for port in 8520 11434 6333; do
    n=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | awk 'NR>1' | wc -l | tr -d ' ')
    echo "port $port listeners: $n"
done
sect "processes (streamlit / ollama)"
pgrep -fl "streamlit run|ollama" 2>/dev/null || echo "(없음)"
sect "install dir (~/내서재_베타) top-level"
if [ -d "$HOME/내서재_베타" ]; then ls -la "$HOME/내서재_베타"; du -sh "$HOME/내서재_베타" 2>/dev/null; else echo "(없음)"; fi
sect "app log tail (beta_app.log)"
LOG="$HOME/내서재_베타/app/beta_app.log"
if [ -f "$LOG" ]; then tail -n 20 "$LOG"; else echo "(없음)"; fi
} > "$OUT" 2>&1
echo "snapshot written: $OUT"
