#!/usr/bin/env python3
"""Teste do gate de conteudo: as 11 obras da rodada + o caso da obra trocada.

Criterio: o texto tem que provar o TITULO **e** o AUTOR. O caso "A Perdição"
(obra trocada por "Minha perdição", de outra autora) tem que ser REJEITADO.
"""
import importlib.util
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
spec = importlib.util.spec_from_file_location("pa", ROOT / "scripts/pipeline-aquisicao.py")
pa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pa)


def corpo(p):
    t = Path(p).read_text(encoding="utf-8")
    return t.split("---", 2)[-1] if t.count("---") >= 2 else t


CASOS = [
    # (nome, caminho relativo, variantes, autor, esperado)
    # A Perdição: a obra TROCADA foi removida do acervo em 2026-11-11, e o
    # ebook com o texto errado foi preservado em /tmp para o teste.
    ("A Perdição", "/tmp/A-Perdicao-ERRADA.md",
     ["A Perdição"], "Eça de Queiroz", False),
    ("O Peregrino", "data/biblioteca/literatura-mundial-classica/ingles/O-Peregrino-John-Bunyan.md",
     ["The Pilgrim's Progress"], "John Bunyan", True),
    ("Tônio Kroeger", "data/biblioteca/literatura-mundial-classica/alemão/Tonio-Kroeger-Thomas-Mann.md",
     ["Tonio Kroeger"], "Thomas Mann", True),
    ("Uma História de Duas Cidades", "data/biblioteca/literatura-mundial-classica/anglo-saxoes/Uma-Historia-de-Duas-Cidades-Charles-Dickens.md",
     ["Um Conto de Duas Cidades"], "Charles Dickens", True),
    ("A Utopia", "data/biblioteca/literatura-mundial-classica/anglo-saxoes/A-Utopia-Joseph-Conrad.md",
     ["Under Western Eyes"], "Joseph Conrad", True),
    ("O Estrangeiro", "data/biblioteca/literatura-mundial-classica/frances/O-Estrangeiro-Albert-Camus.md",
     ["L'Étranger"], "Albert Camus", True),
    ("Sangue Bom", "data/biblioteca/literatura-mundial-classica/ingles/Sangue-Bom-Flannery-OConnor.md",
     ["Good Country People"], "Flannery O'Connor", True),
    ("Um Teto Todo Seu", "data/biblioteca/literatura-mundial-classica/anglo-saxoes/Um-Teto-Todo-Seu-Virginia-Woolf.md",
     ["A Room of One's Own"], "Virginia Woolf", True),
    ("Werther", "data/biblioteca/literatura-mundial-classica/alemão/Werther-J-W-Goethe.md",
     ["Die Leiden des jungen Werthers"], "J. W. Goethe", True),
    ("Seis Personagens", "data/biblioteca/literatura-mundial-classica/italiano/Seis-Personagens-a-Procura-de-um-Autor-Luigi-Pirandello.md",
     ["Sei personaggi in cerca d'autore"], "Luigi Pirandello", True),
    ("Tom Jones", "data/biblioteca/literatura-mundial-classica/frances/Tom-Jones-Henry-Fielding.md",
     ["Tom Jones"], "Henry Fielding", True),
]

falhas = 0
for nome, rel, vars_, aut, esperado in CASOS:
    got = pa.conteudo_confere(corpo(ROOT / rel), nome, vars_, aut)
    ok = got == esperado
    falhas += 0 if ok else 1
    print(f"{'OK   ' if ok else 'FALHA'} {nome:28s} aceito={str(got):5s} esperado={esperado}")

print(f"\n{len(CASOS) - falhas}/{len(CASOS)} casos OK")
raise SystemExit(1 if falhas else 0)
