"""
Extrae el catalogo de triciclos de https://cubancargos.com/triciclos a CSV.

Uso:
    python extraer_triciclos_cubancargos.py

Salidas (en la misma carpeta):
    catalogo_triciclos_cubancargos.csv               -> una fila por producto
    catalogo_triciclos_cubancargos_especificaciones.csv -> formato largo (atributo/valor)

Fuente de datos: JSON-LD (schema.org/Product) + tabla "Especificaciones tecnicas"
de cada ficha de producto. Los enlaces se descubren en las paginas de categoria
y en el sitemap, por lo que el script incorpora automaticamente modelos nuevos.
"""

import csv
import json
import re
import time
import unicodedata
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup

BASE = "https://cubancargos.com"
CATEGORIAS = ["/triciclos", "/triciclos/electricos-cuba", "/triciclos/gasolina-cuba"]
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
}
OUT = Path(__file__).resolve().parent

CORE = [
    "id", "nombre", "tipo_propulsion", "marca_modelo", "motor", "potencia_w",
    "bateria", "autonomia_km", "capacidad_carga_kg", "panel_solar_w", "extensor_rango_w",
    "dimensiones_cama", "garantia", "documentacion", "color", "extras", "equipamiento",
    "precio_usd", "precio_anterior_usd", "ahorro_usd", "descuento_pct",
    "envio_usd", "precio_total_con_envio_usd", "moneda", "dias_entrega",
    "estado_web", "disponibilidad_schema", "rating", "resenas", "sku",
    "categoria", "descripcion", "url", "imagen", "fecha_extraccion", "nota_calidad",
]
USADOS = {
    "Tipo", "Marca", "Modelo", "Motor", "Batería", "Autonomía", "Capacidad de carga",
    "Panel solar", "Extensor de rango", "Dimensiones de cama", "Garantía",
    "Documentación", "Color", "Extras", "Equipamiento",
}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", "replace")


def descubrir_productos():
    urls = set()
    for cat in CATEGORIAS:
        try:
            html = get(BASE + cat)
        except Exception as e:  # noqa: BLE001
            print(f"  aviso: no se pudo leer {cat}: {e}")
            continue
        urls |= set(re.findall(r'href="(/triciclos/[a-z0-9\-]+/[a-z0-9\-]+)"', html))
    try:
        sitemap = get(BASE + "/sitemap.xml")
        urls |= set(re.findall(r"<loc>https://cubancargos\.com(/triciclos/[a-z0-9\-]+/[a-z0-9\-]+)</loc>", sitemap))
    except Exception as e:  # noqa: BLE001
        print(f"  aviso: no se pudo leer el sitemap: {e}")
    return sorted(urls)


def num(v):
    if v in (None, ""):
        return ""
    return float(str(v).replace(",", "").replace("$", "").strip())


def extraer(url):
    soup = BeautifulSoup(get(BASE + url), "lxml")
    ld = {}
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(data, dict) and data.get("@type") == "Product":
            ld = data
    offer = ld.get("offers") or {}
    rating = ld.get("aggregateRating") or {}
    ship = (offer.get("shippingDetails") or {}).get("shippingRate") or {}

    txt = re.sub(r"[ \t]+", " ", soup.get_text("\n"))
    vis = re.search(r"Precio:\s*\$([\d,]+\.\d{2})", txt)
    viejo = re.search(r"Precio:\s*\$[\d,]+\.\d{2}\s*\n\s*\$([\d,]+\.\d{2})", txt)
    dto = re.search(r"\$[\d,]+\.\d{2}\s*\n\s*\$[\d,]+\.\d{2}\s*\n\s*(\d+)%", txt)

    specs, long_rows = {}, []
    h = next((x for x in soup.find_all(["h2", "h3"]) if "Especificaciones" in x.get_text()), None)
    table = h.find_next("table") if h else None
    for tr in (table.find_all("tr") if table else []):
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue
        label = tds[0].get_text(" ", strip=True)
        strong = tds[1].find("span", class_="font-semibold")
        value = strong.get_text(" ", strip=True) if strong else tds[1].get_text(" ", strip=True)
        nota = tds[1].find("span", class_=re.compile("text-gray-400"))
        specs[label] = value
        long_rows.append({"id": url.rsplit("/", 1)[-1], "nombre": ld.get("name", ""),
                          "atributo": label, "valor": value,
                          "nota": nota.get_text(" ", strip=True) if nota else ""})

    crumb = soup.find("nav", attrs={"aria-label": "Breadcrumb"})
    cat = " > ".join(a.get_text(" ", strip=True) for a in crumb.find_all("a")
                     if a.get_text(strip=True)) if crumb else ""

    motor = specs.get("Motor", "")
    w = re.search(r"([\d.]+)\s*W", motor)
    aut = re.search(r"(\d+)\s*[–\-]\s*(\d+)\s*km", specs.get("Autonomía", "")) or \
          re.search(r"(\d+)\s*km", specs.get("Autonomía", ""))
    aut_km = f"{aut.group(1)}-{aut.group(2)}" if aut and aut.lastindex == 2 else (aut.group(1) if aut else "")
    cap = re.search(r"([\d.,]+)\s*kg", specs.get("Capacidad de carga", ""))
    panel = re.search(r"(\d+)\s*W", specs.get("Panel solar", ""))
    ext = re.search(r"(\d+)\s*W", specs.get("Extensor de rango", ""))

    precio = num(offer.get("price") or (vis.group(1) if vis else ""))
    antes = num(viejo.group(1) if viejo else "")

    row = {
        "id": url.rsplit("/", 1)[-1],
        "nombre": ld.get("name", ""),
        "tipo_propulsion": specs.get("Tipo", ""),
        "marca_modelo": " ".join(x for x in [specs.get("Marca", ""), specs.get("Modelo", "")] if x),
        "motor": motor,
        "potencia_w": w.group(1) if w else "",
        "bateria": specs.get("Batería", ""),
        "autonomia_km": aut_km,
        "capacidad_carga_kg": cap.group(1) if cap else "",
        "panel_solar_w": panel.group(1) if panel else "",
        "extensor_rango_w": ext.group(1) if ext else "",
        "dimensiones_cama": specs.get("Dimensiones de cama", ""),
        "garantia": specs.get("Garantía", ""),
        "documentacion": specs.get("Documentación", ""),
        "color": specs.get("Color", ""),
        "extras": specs.get("Extras", ""),
        "equipamiento": specs.get("Equipamiento", ""),
        "precio_usd": precio,
        "precio_anterior_usd": antes,
        "ahorro_usd": round(antes - precio, 2) if antes and precio else "",
        "descuento_pct": dto.group(1) if dto else "",
        "envio_usd": ship.get("value", ""),
        "precio_total_con_envio_usd": round(precio + float(ship.get("value", 0)), 2) if precio else "",
        "moneda": offer.get("priceCurrency", "USD"),
        "dias_entrega": "25-35",
        "estado_web": "Agotado" if "Agotado" in txt else "Disponible",
        "disponibilidad_schema": (offer.get("availability") or "").split("/")[-1],
        "rating": rating.get("ratingValue", ""),
        "resenas": rating.get("reviewCount", ""),
        "sku": ld.get("sku", ""),
        "categoria": cat,
        "descripcion": ld.get("description", ""),
        "url": BASE + url,
        "imagen": ld.get("image", ""),
        "fecha_extraccion": date.today().isoformat(),
        "nota_calidad": "",
    }
    for k, v in specs.items():
        if k not in USADOS:
            key = unicodedata.normalize("NFKD", k).encode("ascii", "ignore").decode()
            row["extra_" + key.lower().replace(" ", "_")] = v
    return row, long_rows


def main():
    print("Descubriendo fichas de triciclos...")
    urls = descubrir_productos()
    print(f"  {len(urls)} productos encontrados")

    rows, long_rows = [], []
    for i, u in enumerate(urls, 1):
        print(f"  [{i}/{len(urls)}] {u}")
        row, lr = extraer(u)
        rows.append(row)
        long_rows += lr
        time.sleep(0.7)

    extra_cols = sorted({k for r in rows for k in r if k.startswith("extra_")})
    cols = CORE + extra_cols
    for r in rows:
        for c in cols:
            r.setdefault(c, "")

    sku_count = Counter(r["sku"] for r in rows if r["sku"])
    for r in rows:
        notas = []
        if r["estado_web"] == "Agotado" and r["disponibilidad_schema"] == "InStock":
            notas.append("Web muestra 'Agotado' pero el JSON-LD declara InStock")
        if r["sku"] and sku_count[r["sku"]] > 1:
            notas.append(f"SKU {r['sku']} repetido en {sku_count[r['sku']]} productos")
        if r["garantia"] and "incluida" in r["garantia"].lower():
            notas.append("Campo 'Garantía' publicado como 'Batería incluida' (posible error del sitio)")
        if not r["autonomia_km"]:
            notas.append("Sin autonomía publicada")
        if not r["capacidad_carga_kg"]:
            notas.append("Sin capacidad de carga publicada")
        if not r["potencia_w"]:
            notas.append("Sin potencia de motor publicada")
        r["nota_calidad"] = "; ".join(notas)
        for k in ["precio_usd", "precio_anterior_usd", "ahorro_usd", "precio_total_con_envio_usd"]:
            if isinstance(r[k], float) and r[k].is_integer():
                r[k] = int(r[k])

    with open(OUT / "catalogo_triciclos_cubancargos.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    with open(OUT / "catalogo_triciclos_cubancargos_especificaciones.csv", "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["id", "nombre", "atributo", "valor", "nota"])
        w.writeheader()
        w.writerows(long_rows)

    print(f"\nListo: {len(rows)} productos, {len(long_rows)} filas de especificaciones.")
    for r in rows:
        print(f"  {r['nombre']:24s} {r['tipo_propulsion']:10s} USD {r['precio_usd']:>6}  {r['estado_web']}")


if __name__ == "__main__":
    main()
