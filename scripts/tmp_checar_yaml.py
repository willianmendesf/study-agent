import yaml
from pathlib import Path

p = Path("/home/willian/study-agent/data/perfil/bibliotecario/estante-william.yaml")
d = yaml.safe_load(p.read_text(encoding="utf-8"))
print("YAML valido. total =", d["total"], "| livros =", len(d["livros"]))
print("primeiro:", d["livros"][0]["titulo"], "|", d["livros"][0]["autor"])
print("ultimo:", d["livros"][-1]["titulo"])
print("eixos:", sorted({l["eixo"] for l in d["livros"]}))
