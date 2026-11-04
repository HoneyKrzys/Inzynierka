from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.pagesizes import A4


def utworz_pdf(title, patient, doctor, sections, identifier):
    font = (
        Path(settings.BASE_DIR)
        / "clinic"
        / "static"
        / "clinic"
        / "fonts"
        / "DejaVuSans.ttf"
    )
    if "Gabinet" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("Gabinet", str(font)))
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="BodyPL",
            fontName="Gabinet",
            fontSize=10,
            leading=15,
            spaceAfter=8,
            wordWrap="LTR",
        )
    )
    styles.add(
        ParagraphStyle(
            name="TitlePL",
            fontName="Gabinet",
            fontSize=22,
            leading=28,
            textColor=colors.HexColor("#173d43"),
            spaceAfter=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="LabelPL",
            fontName="Gabinet",
            fontSize=11,
            leading=16,
            textColor=colors.HexColor("#0f766e"),
            spaceBefore=12,
            spaceAfter=5,
        )
    )

    def akapit(text, style="BodyPL"):
        return Paragraph(escape(str(text)).replace("\n", "<br/>"), styles[style])

    story = [
        akapit("MEDYCYNA JAK DAWNIEJ", "LabelPL"),
        akapit(title, "TitlePL"),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#c9d8d6")),
        Spacer(1, 12),
        akapit(f"Pacjent: {patient}"),
        akapit(f"Lekarz: {doctor}"),
        akapit(f"Numer: {identifier}"),
    ]
    for label, text in sections:
        story.extend([akapit(label, "LabelPL"), akapit(text or "Nie podano")])

    def stopka(canvas, doc):
        canvas.setFont("Gabinet", 8)
        canvas.setFillColor(colors.HexColor("#687b7d"))
        canvas.drawString(42, 28, "Medycyna jak dawniej")
        canvas.drawRightString(A4[0] - 42, 28, f"Strona {doc.page}")

    SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=42,
        leftMargin=42,
        topMargin=40,
        bottomMargin=48,
        title=title,
        author="Medycyna jak dawniej",
    ).build(story, onFirstPage=stopka, onLaterPages=stopka)
    return buffer.getvalue()
