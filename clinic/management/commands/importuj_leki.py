from datetime import date
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from clinic.models import ProduktLeczniczy, OpakowanieLeku

NS = "{http://rejestry.ezdrowie.gov.pl/rpl/eksport-danych-v6.0.0}"


class Command(BaseCommand):
    help = "Import oficjalnego eksportu RPL XML v6; tylko produkty ludzkie."

    def add_arguments(self, parser):
        parser.add_argument("file")

    def handle(self, *args, **options):
        path = Path(options["file"])
        root = ET.parse(path).getroot()
        if root.tag != NS + "produktyLecznicze":
            raise CommandError("Nieobsługiwany format XML.")
        source_date = date.fromisoformat(root.attrib["stanNaDzien"])
        products, packages = [], []
        for node in root:
            a = node.attrib
            if a.get("rodzajPreparatu") != "ludzki":
                continue
            products.append(
                ProduktLeczniczy(
                    rpl_id=a["id"],
                    name=a["nazwaProduktu"],
                    form=a.get("nazwaPostaciFarmaceutycznej", ""),
                    strength=a.get("moc", ""),
                    substance=a.get("nazwaPowszechnieStosowana", ""),
                    source_date=source_date,
                    active=True,
                )
            )
            for package in node.findall(f"{NS}opakowania/{NS}opakowanie"):
                if package.get("skasowane") != "NIE":
                    continue
                units = []
                for unit in package.findall(
                    f"{NS}jednostkiOpakowania/{NS}jednostkaOpakowania"
                ):
                    u = unit.attrib
                    description = " ".join(
                        filter(
                            None, [u.get("liczbaOpakowan"), u.get("rodzajOpakowania")]
                        )
                    )
                    capacity = " ".join(
                        filter(None, [u.get("pojemnosc"), u.get("jednostkaPojemnosci")])
                    )
                    if capacity:
                        description = (
                            description + " × " if description else ""
                        ) + capacity
                    if u.get("informacjeDodatkowe"):
                        description += " (" + u["informacjeDodatkowe"] + ")"
                    units.append(description)
                packages.append(
                    (
                        a["id"],
                        package.attrib["id"],
                        " + ".join(units) or "Nie podano",
                        package.get("kodGTIN", ""),
                        package.get("kategoriaDostepnosci", ""),
                    )
                )
        if not products or not packages:
            raise CommandError("Pusty wykaz — import przerwany.")
        with transaction.atomic():
            ProduktLeczniczy.objects.update(active=False)
            ProduktLeczniczy.objects.bulk_create(
                products,
                batch_size=1000,
                update_conflicts=True,
                unique_fields=["rpl_id"],
                update_fields=[
                    "name",
                    "form",
                    "strength",
                    "substance",
                    "source_date",
                    "active",
                ],
            )
            mapping = dict(
                ProduktLeczniczy.objects.filter(active=True).values_list("rpl_id", "pk")
            )
            OpakowanieLeku.objects.all().delete()
            OpakowanieLeku.objects.bulk_create(
                [
                    OpakowanieLeku(
                        product_id=mapping[p],
                        rpl_id=i,
                        description=d,
                        gtin=g,
                        availability=a,
                    )
                    for p, i, d, g, a in packages
                ],
                batch_size=1000,
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Produkty: {len(products)}; opakowania: {len(packages)}; stan: {source_date}"
            )
        )
        path.with_suffix(".metadata.json").write_text(
            json.dumps(
                {
                    "source": "https://rejestry.ezdrowie.gov.pl/api/rpl/medicinal-products/public-pl-report/6.0.0/overall.xml",
                    "source_date": str(source_date),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "products": len(products),
                    "packages": len(packages),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
