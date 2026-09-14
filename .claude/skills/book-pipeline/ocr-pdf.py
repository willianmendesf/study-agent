#!/usr/bin/env python3
"""OCR de PDF escaneado via pdftoppm + EasyOCR.
Uso: ocr-pdf.py <pdf_input> <md_output>
"""
import sys, subprocess, tempfile, os
from pathlib import Path
import easyocr

def main():
    pdf = Path(sys.argv[1])
    out = Path(sys.argv[2])

    print(f"📄 {pdf.name} ({pdf.stat().st_size//(1024*1024)} MB)", flush=True)

    with tempfile.TemporaryDirectory(prefix='ocr-') as tmpdir:
        tmp = Path(tmpdir)
        print("  → pdftoppm 200dpi...", flush=True)
        subprocess.run(['pdftoppm', '-r', '200', '-png', str(pdf), str(tmp / 'page')],
                       check=True, capture_output=True)
        pages = sorted(tmp.glob('page-*.png'))
        print(f"  → {len(pages)} páginas", flush=True)

        print("  → EasyOCR carregando (pt+en)...", flush=True)
        reader = easyocr.Reader(['pt', 'en'], gpu=False)

        resultados = []
        for i, p in enumerate(pages, 1):
            result = reader.readtext(str(p), detail=0, paragraph=True)
            texto = '\n'.join(result).strip()
            resultados.append(f"\n\n---\n# Página {i:03d}\n\n{texto}\n")
            if i % 10 == 0:
                print(f"  ✓ página {i}/{len(pages)}", flush=True)

        out.write_text(f"# OCR — {pdf.stem}\n\n" + ''.join(resultados), encoding='utf-8')
        print(f"  ✅ {out} ({out.stat().st_size//1024} KB)", flush=True)

if __name__ == '__main__':
    main()