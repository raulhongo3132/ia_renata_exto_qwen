from pathlib import Path
from markitdown import MarkItDown

PDF_DIR = Path("historicos/pdf")
MD_DIR = Path("historicos/md")
MD_DIR.mkdir(parents=True, exist_ok=True)

conv = MarkItDown()
ok, vacios, errores = 0, [], []

for pdf in sorted(PDF_DIR.glob("REP-*.pdf")):
    try:
        texto = conv.convert(str(pdf)).text_content
    except Exception as e:
        errores.append((pdf.name, str(e)))
        continue
    if len(texto.strip()) < 50:
        vacios.append(pdf.name)
        continue
    (MD_DIR / f"{pdf.stem}.md").write_text(texto, encoding="utf-8")
    ok += 1

print(f"Convertidos: {ok}")
print(f"Vacíos (posible PDF de imagen): {vacios}")
print(f"Errores: {errores}")
