#!/bin/sh
# Executa o deja-vu com o binario deste SO/arquitetura (pastas <so>_<arch>/ ao lado deste arquivo).
# Sem binario compativel, usa o `deja` do PATH; sem nenhum, sai em silencio (hooks nunca podem falhar).
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
case "$(uname -s 2>/dev/null)" in
  Linux*) OS=linux; EXT= ;;
  Darwin*) OS=darwin; EXT= ;;
  MINGW*|MSYS*|CYGWIN*) OS=windows; EXT=.exe ;;
  *) OS=; EXT= ;;
esac
case "$(uname -m 2>/dev/null)" in
  x86_64|amd64) ARCH=amd64 ;;
  arm64|aarch64) ARCH=arm64 ;;
  *) ARCH= ;;
esac
BIN="$DIR/${OS}_${ARCH}/deja$EXT"
if [ -n "$OS" ] && [ -n "$ARCH" ] && [ -f "$BIN" ]; then
  [ -x "$BIN" ] || chmod +x "$BIN" 2>/dev/null
  exec "$BIN" "$@"
fi
if command -v deja >/dev/null 2>&1; then exec deja "$@"; fi
if [ "${1:-}" = "mcp" ]; then
  echo "deja: sem binario para ${OS:-?}/${ARCH:-?}; instale: brew install deja-vu | scoop install deja-vu" >&2
  exit 1
fi
exit 0
