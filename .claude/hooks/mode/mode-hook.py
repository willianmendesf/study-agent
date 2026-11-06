#!/usr/bin/env python3
"""mode-hook.py — process hook do picoclaw que implementa o /mode [especialista].

PEDIDO DO WILLIAM (2026-11-05):
  "quero tbm ter como alterar no telegram pra esse e qualquer especialista, pra
   tratar de temas especifico configure isso por favor, assim eu consigo usar
   um /mode [nome do agente] e dai consigo falar e tratar assuntos especificos
   que quero/preciso com a persona/especialista especifico"

POR QUE UM HOOK E NAO UM COMANDO NATIVO:
  O picoclaw tem `/use <skill>` (arma uma SKILL do diretorio de skills), mas
  os 22 especialistas do Study-Agent NAO sao skills — sao personas com
  `data/perfil/especialistas/<nome>.yaml` (instrucoes, protocolo, tags,
  quando_ativar). `/use` nao as alcanca.

  O picoclaw nao tem comandos customizados via config (verificado no codigo:
  `pkg/config/config.go` nao tem campo de comandos; `pkg/commands/builtin.go`
  so registra os builtins). Entao o caminho e' o sistema de HOOKS, que o
  picoclaw suporta via JSON-RPC 2.0 por stdio (docs/architecture/hooks/).

COMO FUNCIONA:
  1. `hook.before_llm` — o hook ve as mensagens do turno. Se a ultima mensagem
     do usuario for `/mode <alvo>`, o hook:
       - resolve `<alvo>` contra os especialistas (nome, apelido, `nome_direto`,
         gatilhos fraseais);
       - SALVA o modo ativo em `data/perfil/modos/ativo.json` (por chat_id);
       - REESCREVE a mensagem para o LLM com o bloco de papel do especialista
         (instrucoes + protocolo + regras), de modo que a resposta saia no
         registro da persona;
       - devolve `action: modify` com as mensagens modificadas.
  2. O bloco injetado é prefixado em TODO turno enquanto o modo estiver
     ativo — assim o "/mode dokimia" muda o comportamento nas mensagens
     seguintes, ate `/mode off`.

O QUE O HOOK NAO FAZ (limites honestos):
  - Nao muda o modelo, nem o canal, nem o system prompt do picoclaw.
  - Nao pode "transformar" a IA em outra pessoa: ele INJETA o papel. A
   o efeito depende do LLM obedecer — mas o papel entra como instrucao do
    usuario + material de referencia, que e o que o orquestrador ja faz.
  - `/mode` e por SESSAO (chat_id). Nao e global.

SEGURANCA:
  - Nunca imprime o token do Telegram.
  - Le o YAML dos especialistas com `yaml.safe_load`.
  - O arquivo de estado fica em `data/perfil/modos/ativo.json` (versionado).
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ESP_DIR = ROOT / "data" / "perfil" / "especialistas"
STATE = ROOT / "data" / "perfil" / "modos" / "ativo.json"
PERFIS = ROOT / "data" / "perfil" / "perfis.md"

# modo default: o orquestrador normal
MODO_OFF = "off"


# --------------------------------------------------------------------------
# JSON-RPC (stdio)
# --------------------------------------------------------------------------
def send(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def reply(rid, result):
    send({"jsonrpc": "2.0", "id": rid, "result": result})


def err(rid, msg):
    send({"jsonrpc": "2.0", "id": rid, "error": {"code": -32000, "message": msg}})


# --------------------------------------------------------------------------
# especialistas
# --------------------------------------------------------------------------
def _yaml():
    try:
        import yaml
        return yaml
    except ImportError:
        return None


def carregar_especialistas():
    """{slug: {titulo, aliases, instr, proto, dominio}} de todos os YAMLs."""
    yaml = _yaml()
    out = {}
    if not ESP_DIR.is_dir():
        return out
    for f in sorted(ESP_DIR.glob("*.yaml")):
        try:
            if yaml:
                d = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            else:
                d = {}
            e = d.get("especialista") or {}
            if not e:
                continue
            wa = e.get("quando_ativar") or {}
            aliases = set()
            for a in (wa.get("nome_direto") or []):
                aliases.add(str(a).strip().lower())
            aliases.add(f.stem.lower())
            slug = f.stem.lower()
            out[slug] = {
                "slug": slug,
                "titulo": e.get("titulo") or slug,
                "aliases": aliases,
                "instr": (e.get("instrucoes") or "").strip(),
                "proto": (e.get("protocolo") or "").strip(),
                "dominio": re.sub(r"\s+", " ", (e.get("dominio") or "")).strip(),
                "descricao": re.sub(r"\s+", " ", (e.get("descricao") or "")).strip(),
            }
        except Exception:
            continue
    return out


def normalizar(s):
    s = (s or "").strip().lower()
    s = re.sub(r"[_\-]+", " ", s)
    s = re.sub(r"[^a-z0-9áàâãéêíóôõúüç ]+", "", s)
    return re.sub(r"\s+", " ", s).strip()


def resolver(alvo, esp):
    """Resolve o alvo digitado -> slug do especialista. None se nao achou."""
    a = normalizar(alvo)
    if not a:
        return None
    # 1. match exato do slug
    for slug, d in esp.items():
        if normalizar(slug) == a:
            return slug
    # 2. match de alias exato
    for slug, d in esp.items():
        if a in {normalizar(x) for x in d["aliases"]}:
            return slug
    # 3. alias contido / slug contido
    for slug, d in esp.items():
        for al in d["aliases"]:
            na = normalizar(al)
            if na and (na in a or a in na):
                return slug
    # 4. fuzzy (difflib) — so acima de um limiar
    import difflib
    nomes = {normalizar(slug): slug for slug in esp}
    for al in esp.values():
        for x in al["aliases"]:
            nomes[normalizar(x)] = slug
    best = difflib.get_close_matches(a, list(nomes.keys()), n=1, cutoff=0.75)
    if best:
        return nomes[best[0]]
    return None


# --------------------------------------------------------------------------
# estado
# --------------------------------------------------------------------------
def ler_estado():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def salvar_estado(st):
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(STATE)
    except Exception:
        pass


def modos_ativos(st, chat_id):
    return (st.get("modos") or {}).get(str(chat_id))


# --------------------------------------------------------------------------
# injecao
# --------------------------------------------------------------------------
def bloco_modo(slug, esp):
    """O texto do papel que entra na mensagem do usuario."""
    d = esp.get(slug)
    if not d:
        return ""
    p = []
    p.append("")
    p.append("=== MODO ATIVO: %s ===" % d["titulo"])
    p.append("")
    p.append("Voce esta respondendo COMO o especialista acima. Use o dominio, as")
    p.append("instrucoes e o protocolo dele. Se o pedido sair do escopo do")
    p.append("especialista, diga isso e ofereca o caminho certo — mas nao mude de")
    p.append("personalidade por conta propria.")
    p.append("")
    if d["dominio"]:
        p.append("[DOMINIO]")
        p.append(d["dominio"])
        p.append("")
    if d["descricao"]:
        p.append("[PAPEL]")
        p.append(d["descricao"])
        p.append("")
    if d["instr"]:
        p.append("[INSTRUCOES]")
        p.append(d["instr"])
        p.append("")
    if d["proto"]:
        p.append("[PROTOCOLO]")
        p.append(d["proto"])
        p.append("")
    p.append("=== FIM DO MODO %s ===" % slug.upper())
    p.append("")
    return "\n".join(p)


def lista_especialistas(esp):
    linhas = []
    for slug, d in sorted(esp.items()):
        linhas.append("- %s — %s" % (slug, d["titulo"]))
    return "\n".join(linhas)


# --------------------------------------------------------------------------
# handler do hook
# --------------------------------------------------------------------------
def before_llm(params):
    msgs = params.get("messages") or []
    chat_id = str(params.get("chat_id") or "")
    esp = carregar_especialistas()

    if not msgs:
        return {"action": "continue"}

    ultima_usuario = None
    for m in reversed(msgs):
        if m.get("role") == "user":
            ultima_usuario = m
            break
    if ultima_usuario is None:
        return {"action": "continue"}

    texto = ultima_usuario.get("content") or ""
    if not isinstance(texto, str):
        return {"action": "continue"}

    st = ler_estado()
    modo_atual = modos_ativos(st, chat_id)
    m_cmd = re.match(r"^\s*[!/]mode(?:\s+([^\n]*))?\s*$", texto, re.I)

    # ---- comando /mode ----
    if m_cmd:
        arg = (m_cmd.group(1) or "").strip()
        if not arg:
            nova = (
                "Modo atual: %s\n\nEspecialistas disponiveis (use /mode <nome>):\n%s"
                % (modo_atual or MODO_OFF, lista_especialistas(esp))
            )
            return _modify_text(ultima_usuario, nova)

        if normalizar(arg) in ("off", "sair", "clear", "none", "normal", "desligar"):
            st.setdefault("modos", {})[str(chat_id)] = None
            salvar_estado(st)
            return _modify_text(
                ultima_usuario,
                "Modo desligado. Volto ao modo padrao (orquestrador).",
            )

        slug = resolver(arg, esp)
        if not slug:
            return _modify_text(
                ultima_usuario,
                "Nao encontrei o especialista '%s'.\n\nDisponiveis:\n%s"
                % (arg, lista_especialistas(esp)),
            )

        st.setdefault("modos", {})[str(chat_id)] = slug
        salvar_estado(st)
        d = esp[slug]
        return _modify_text(
            ultima_usuario,
            "Modo ativado: %s (%s).\n\n%s\nA partir de agora eu respondo neste modo. "
            "Para sair: /mode off."
            % (slug, d["titulo"], bloco_modo(slug, esp)),
        )

    # ---- injecao do modo ja ativo ----
    if modo_atual and modo_atual in esp:
        bloco = bloco_modo(modo_atual, esp)
        if bloco and bloco.strip() not in texto:
            novo = bloco + texto
            idx = msgs.index(ultima_usuario)
            msgs2 = list(msgs)
            msgs2[idx] = dict(ultima_usuario)
            msgs2[idx]["content"] = novo
            return {"action": "modify",
                    "request": {"messages": msgs2}}

    return {"action": "continue"}


def _modify_text(msg_ultima, novo_texto):
    """Sinal pro LLM sem historico; o texto novo vai como ultima mensagem."""
    return {
        "action": "modify",
        "request": {
            "messages": [
                {"role": "user", "content": novo_texto},
            ]
        },
    }


# --------------------------------------------------------------------------
# loop principal
# --------------------------------------------------------------------------
def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        method = msg.get("method")
        rid = msg.get("id")

        if method == "hook.hello":
            reply(rid, {"ok": True, "name": "mode-hook"})
            continue
        if method == "hook.before_llm":
            try:
                params = msg.get("params") or {}
                res = before_llm(params)
                reply(rid, res)
            except Exception as e:
                reply(rid, {"action": "continue"})
            continue
        if method == "hook.after_llm":
            reply(rid, {"action": "continue"})
            continue
        if rid is not None and method is None:
            # resposta a um request nosso
            continue


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
