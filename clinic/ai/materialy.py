import re
from django.conf import settings
from django.db import transaction
from pypdf import PdfReader
from ..models import FragmentMaterialu

from .polaczenie import polacz_z_modelem

def uporzadkuj_tekst_materialu(text, vocabulary=None):
    if vocabulary is None:
        vocabulary = {word.casefold() for word in re.findall(r"[^\W\d_]+", text)}

    text = re.sub(r"(?<=\w)[ \t]*\u00ad[ \t]*\r?\n[ \t]*(?=\w)", "", text)
    text = text.replace("\u00ad", "")

    def polacz_wyraz(match):
        left, right = match.groups()
        joined = left + right


        if right[0].islower() and joined.casefold() in vocabulary:
            return joined
        return left + "-" + right

    text = re.sub(r"([^\W\d_]{2,})[ \t]*[-\u2010][ \t]*\r?\n[ \t]*([^\W\d_]{2,})", polacz_wyraz, text)
    return " ".join(text.replace("/uni00A0", " ").split())


def podziel_material(pages):
    pages = list(pages)
    vocabulary = {word.casefold() for _, text in pages for word in re.findall(r"[^\W\d_]+", text)}
    parts = []
    for page, text in pages:
        text = uporzadkuj_tekst_materialu(text, vocabulary)
        for start in range(0, len(text), 1000):
            fragment = text[start:start + 1200].strip()
            if fragment:
                parts.append((page, fragment))
    return parts


def odczytaj_material(upload):
    if upload.name.lower().endswith(".pdf"):
        reader = PdfReader(upload)
        if len(reader.pages) > 100:
            raise ValueError(
                "Importuj najwyżej 100 stron jednocześnie (np. wybrany rozdział)."
            )
        pages = [
            (i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)
        ]
    else:
        pages = [(1, upload.read().decode("utf-8-sig"))]
    if sum(len(text) for _, text in pages) > 120000:
        raise ValueError("Podziel materiał na mniejsze części — limit 120 000 znaków.")
    parts = podziel_material(pages)
    if not parts:
        raise ValueError("Nie znaleziono tekstu. Skany wymagają wcześniejszego OCR.")
    return parts


def zapisz_fragmenty(source, parts):
    embeddings = []
    engine = polacz_z_modelem()
    for start in range(0, len(parts), 8):
        embeddings.extend(
            engine.embed(
                model=settings.OLLAMA_EMBED_MODEL,
                input=[p[1] for p in parts[start : start + 8]],
            ).embeddings
        )
    if len(embeddings) != len(parts) or any(not v for v in embeddings):
        raise ValueError("Model nie zwrócił kompletu embeddingów.")
    with transaction.atomic():
        source.save()
        FragmentMaterialu.objects.bulk_create(
            [
                FragmentMaterialu(source=source, page=page, text=text, embedding=vector)
                for (page, text), vector in zip(parts, embeddings)
            ]
        )
        source.embedding_model = settings.OLLAMA_EMBED_MODEL
        source.save(update_fields=["embedding_model"])

