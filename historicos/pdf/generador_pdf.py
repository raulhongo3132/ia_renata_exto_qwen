from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

ARCHIVO_ENTRADA = Path("historicos/txt/reportes_176_200.txt")
CARPETA_SALIDA = Path("historicos/pdf")


# ============================================================
# FUNCIONES
# ============================================================

def leer_reportes(archivo):
    """Lee el TXT y devuelve una lista de reportes."""
    contenido = archivo.read_text(encoding="utf-8")

    bloques = re.findall(
        r"=== REPORTE ===(.*?)=== FIN ===",
        contenido,
        re.DOTALL
    )

    reportes = []

    for bloque in bloques:
        bloque = bloque.strip()

        # Busca cada campo con formato:
        # Campo: valor
        patron = re.compile(
            r"(ID|Fecha|Sucursal|Reportado por|Tipo|Prioridad|"
            r"Descripción del problema|Causa encontrada|"
            r"Solución aplicada|Técnico|Tiempo de resolución):\s*(.*?)(?=\n?\s*"
            r"(?:ID|Fecha|Sucursal|Reportado por|Tipo|Prioridad|"
            r"Descripción del problema|Causa encontrada|"
            r"Solución aplicada|Técnico|Tiempo de resolución):|$)",
            re.DOTALL
        )

        datos = {}

        for campo, valor in patron.findall(bloque):
            datos[campo] = " ".join(valor.split())

        if "ID" in datos:
            reportes.append(datos)

    return reportes


def generar_pdf(reporte, archivo_salida):
    """Genera un PDF individual para un reporte."""

    estilos = getSampleStyleSheet()

    titulo = ParagraphStyle(
        "Titulo",
        parent=estilos["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1F2937"),
        spaceAfter=18,
    )

    subtitulo = ParagraphStyle(
        "Subtitulo",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#6B7280"),
        spaceAfter=18,
    )

    etiqueta = ParagraphStyle(
        "Etiqueta",
        parent=estilos["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=colors.white,
    )

    valor = ParagraphStyle(
        "Valor",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#111827"),
    )

    texto = ParagraphStyle(
        "Texto",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        textColor=colors.HexColor("#111827"),
        spaceAfter=8,
    )

    # Márgenes
    doc = SimpleDocTemplate(
        str(archivo_salida),
        pagesize=LETTER,
        rightMargin=1.7 * cm,
        leftMargin=1.7 * cm,
        topMargin=1.7 * cm,
        bottomMargin=1.7 * cm,
        title=f"Reporte {reporte.get('ID', '')}",
        author="Sistema de reportes",
    )

    elementos = []

    # Encabezado
    elementos.append(
        Paragraph(
            f"REPORTE DE SOPORTE — {reporte.get('ID', '')}",
            titulo
        )
    )

    elementos.append(
        Paragraph(
            "Registro histórico de incidencia",
            subtitulo
        )
    )

    # Información general
    campos_generales = [
        ("Fecha", reporte.get("Fecha", "")),
        ("Sucursal", reporte.get("Sucursal", "")),
        ("Reportado por", reporte.get("Reportado por", "")),
        ("Tipo", reporte.get("Tipo", "")),
        ("Prioridad", reporte.get("Prioridad", "")),
        ("Técnico", reporte.get("Técnico", "")),
        ("Tiempo de resolución", reporte.get("Tiempo de resolución", "")),
    ]

    tabla_datos = []

    for campo, valor_campo in campos_generales:
        tabla_datos.append([
            Paragraph(campo, etiqueta),
            Paragraph(valor_campo, valor),
        ])

    tabla = Table(
        tabla_datos,
        colWidths=[5 * cm, 11.5 * cm],
        repeatRows=0,
    )

    tabla.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.HexColor("#2563EB"),
            ),
            (
                "BACKGROUND",
                (1, 0),
                (1, -1),
                colors.HexColor("#F3F4F6"),
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor("#D1D5DB"),
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP",
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                8,
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                8,
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                7,
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                7,
            ),
        ])
    )

    elementos.append(tabla)
    elementos.append(Spacer(1, 20))

    # Descripción
    elementos.append(
        Paragraph("Descripción del problema", estilos["Heading2"])
    )

    elementos.append(
        Paragraph(
            reporte.get("Descripción del problema", ""),
            texto
        )
    )

    # Causa
    elementos.append(
        Paragraph("Causa encontrada", estilos["Heading2"])
    )

    elementos.append(
        Paragraph(
            reporte.get("Causa encontrada", ""),
            texto
        )
    )

    # Solución
    elementos.append(
        Paragraph("Solución aplicada", estilos["Heading2"])
    )

    elementos.append(
        Paragraph(
            reporte.get("Solución aplicada", ""),
            texto
        )
    )

    # Pie de página
    def agregar_pie(canvas, doc):
        canvas.saveState()

        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#6B7280"))

        canvas.drawString(
            1.7 * cm,
            1 * cm,
            f"Reporte {reporte.get('ID', '')}"
        )

        canvas.drawRightString(
            LETTER[0] - 1.7 * cm,
            1 * cm,
            f"Página {doc.page}"
        )

        canvas.restoreState()

    doc.build(
        elementos,
        onFirstPage=agregar_pie,
        onLaterPages=agregar_pie,
    )


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():
    if not ARCHIVO_ENTRADA.exists():
        print(f"ERROR: No existe el archivo:")
        print(f"  {ARCHIVO_ENTRADA}")
        return

    # Crear carpeta de salida si no existe
    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)

    # Leer reportes
    reportes = leer_reportes(ARCHIVO_ENTRADA)

    if not reportes:
        print("ERROR: No se encontraron reportes en el archivo.")
        return

    print(f"Se encontraron {len(reportes)} reportes.")
    print()

    # Generar un PDF por reporte
    for reporte in reportes:
        reporte_id = reporte.get("ID", "SIN_ID")

        # Evita caracteres problemáticos en nombres
        nombre_archivo = re.sub(
            r'[<>:"/\\|?*]',
            "_",
            reporte_id
        )

        archivo_pdf = CARPETA_SALIDA / f"{nombre_archivo}.pdf"

        generar_pdf(
            reporte,
            archivo_pdf
        )

        print(f"Generado: {archivo_pdf}")

    print()
    print("Proceso terminado.")
    print(f"PDF generados: {len(reportes)}")
    print(f"Carpeta: {CARPETA_SALIDA}")


if __name__ == "__main__":
    main()