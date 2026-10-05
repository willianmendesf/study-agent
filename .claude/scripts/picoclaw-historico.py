#!/usr/bin/env python3
"""Arquiva as conversas do picoclaw e as expoe ao deja-vu.

Para cada sessao em <workspace>/sessions/*.jsonl (formato picoclaw: role/content/tool_calls):
  1. data/historico/picoclaw/<data>_<chave8>.md   transcrito legivel (usuario + assistente; saida de ferramenta omitida)
  2. data/historico/picoclaw/bruto/<chave>.jsonl  copia fiel do original
  3. data/historico/picoclaw/INDEX.md             indice por data/sessao
  4. ~/.claude/projects/-<workspace>/<uuid>.jsonl  transcrito no formato do Claude Code (o deja indexa este)

Idempotente: so reprocessa sessao cuja assinatura (mtime:tamanho) mudou. Sem dependencias externas.
Uso: python3 .claude/scripts/picoclaw-historico.py [--workspace DIR] [--home DIR]
"""
import argparse, datetime as dt, json, os, re, uuid
from pathlib import Path

SEGREDO = re.compile(
    r"(sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|"
    r"(?i:(?:senha|password|passwd|token|api[_-]?key|secret)\s*[:=]\s*)\S{6,})")


def limpar(texto):
    return SEGREDO.sub("[REDIGIDO]", texto or "")


def ler_sessao(caminho):
    msgs = []
    for linha in caminho.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            msgs.append(json.loads(linha))
        except json.JSONDecodeError:
            continue
    return msgs


def texto_de(msg):
    c = msg.get("content")
    if isinstance(c, list):
        c = " ".join(b.get("text", "") for b in c if isinstance(b, dict))
    return (c or "").strip()


def chamadas(msg):
    return [tc.get("function", {}).get("name", "?") for tc in msg.get("tool_calls") or []]


def render_md(chave, msgs, meta, modelo, quando):
    resumo = (meta.get("summary") or "").strip().replace("\n", " ")[:400]
    n_user = sum(1 for m in msgs if m.get("role") == "user")
    fm = [
        "---",
        "origem: picoclaw",
        f"sessao: {chave}",
        f"modelo: {modelo or 'desconhecido'}",
        f"atualizado: {quando.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"mensagens_usuario: {n_user}",
        "tipo: historico-conversa",
        f"resumo: \"{limpar(resumo).replace(chr(34), chr(39))}\"",
        "---",
        "",
    ]
    corpo = []
    for m in msgs:
        papel = m.get("role")
        if papel == "user":
            corpo += ["## Usuário", "", limpar(texto_de(m)), ""]
        elif papel == "assistant":
            t = limpar(texto_de(m))
            ferr = chamadas(m)
            if t:
                corpo += ["## Assistente", "", t, ""]
            if ferr:
                corpo += [f"> ferramentas: {', '.join(ferr)}", ""]
    return "\n".join(fm + corpo)


def render_claude(chave, msgs, modelo, quando, cwd):
    sid = str(uuid.uuid5(uuid.NAMESPACE_URL, "picoclaw:" + chave))
    util = [m for m in msgs if m.get("role") in ("user", "assistant") and texto_de(m)]
    saida, pai = [], None
    for i, m in enumerate(util):
        ts = quando - dt.timedelta(seconds=2 * (len(util) - 1 - i))
        uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{sid}:{i}"))
        base = {
            "parentUuid": pai, "isSidechain": False, "uuid": uid, "sessionId": sid,
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S.000Z"), "cwd": cwd,
            "userType": "external", "entrypoint": "picoclaw", "version": "picoclaw",
        }
        texto = limpar(texto_de(m))
        if m["role"] == "user":
            base |= {"type": "user", "message": {"role": "user", "content": texto}}
        else:
            base |= {"type": "assistant", "message": {
                "role": "assistant", "model": modelo or "picoclaw",
                "content": [{"type": "text", "text": texto}]}}
        saida.append(json.dumps(base, ensure_ascii=False))
        pai = uid
    return sid, "\n".join(saida) + ("\n" if saida else "")


def gravar(destino, conteudo):
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(destino.suffix + ".tmp")
    tmp.write_text(conteudo, encoding="utf-8")
    os.replace(tmp, destino)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default="/home/study-agent")
    ap.add_argument("--home", default=str(Path.home()))
    a = ap.parse_args()
    ws = Path(a.workspace)
    sessoes = ws / "sessions"
    raiz = ws / "data" / "historico" / "picoclaw"
    estado_f = raiz / ".estado.json"
    estado = json.loads(estado_f.read_text()) if estado_f.exists() else {}
    proj = Path(a.home) / ".claude" / "projects" / ("-" + str(ws).strip("/").replace("/", "-"))

    novos = 0
    for jl in sorted(sessoes.glob("*.jsonl")):
        chave = jl.stem
        st = jl.stat()
        sig = f"{int(st.st_mtime)}:{st.st_size}"
        reg = estado.get(chave, {})
        if reg.get("sig") == sig:
            continue
        msgs = ler_sessao(jl)
        if not msgs:
            continue
        mp = jl.with_suffix(".meta.json")
        meta = json.loads(mp.read_text()) if mp.exists() else {}
        modelo = next((m.get("model_name") for m in msgs if m.get("model_name")), None)
        quando = dt.datetime.fromtimestamp(st.st_mtime, dt.timezone.utc)
        nome = reg.get("arquivo") or f"{quando.strftime('%Y-%m-%d')}_{chave[-8:]}.md"
        gravar(raiz / nome, render_md(chave, msgs, meta, modelo, quando))
        gravar(raiz / "bruto" / jl.name, jl.read_text(encoding="utf-8", errors="replace"))
        sid, cl = render_claude(chave, msgs, modelo, quando, str(ws))
        gravar(proj / f"{sid}.jsonl", cl)
        estado[chave] = {"sig": sig, "arquivo": nome,
                         "resumo": (meta.get("summary") or "")[:120].replace("\n", " ")}
        novos += 1

    if novos or not (raiz / "INDEX.md").exists():
        linhas = ["# Histórico de conversas do picoclaw", "",
                  "Gerado por `.claude/scripts/picoclaw-historico.py` (bruto; não editar à mão).", "",
                  "| Arquivo | Resumo |", "|---|---|"]
        for ch, r in sorted(estado.items(), key=lambda kv: kv[1]["arquivo"], reverse=True):
            linhas.append(f"| [{r['arquivo']}]({r['arquivo']}) | {limpar(r.get('resumo', '')) or '—'} |")
        gravar(raiz / "INDEX.md", "\n".join(linhas) + "\n")
        gravar(estado_f, json.dumps(estado, ensure_ascii=False, indent=1))
    print(f"picoclaw-historico: {novos} sessao(oes) atualizada(s), {len(estado)} no total")


if __name__ == "__main__":
    main()
