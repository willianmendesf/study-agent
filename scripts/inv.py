#!/usr/bin/env python3
"""Inventário rápido da biblioteca: lista pastas e arquivos de interesse."""
import os, sys, re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def listdir(p):
    try:
        return sorted(os.listdir(p))
    except Exception as e:
        return [f"<erro: {e}>"]

if __name__ == "__main__":
    for arg in sys.argv[1:]:
        p = os.path.join(BASE, arg)
        print(f"== {arg} ==")
        for name in listdir(p):
            full = os.path.join(p, name)
            if os.path.isdir(full):
                n = len(os.listdir(full))
                print(f"  [dir] {name}/ ({n} itens)")
            else:
                size = os.path.getsize(full)
                print(f"  {name} ({size//1024} KB)")
