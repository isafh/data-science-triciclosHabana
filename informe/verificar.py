# -*- coding: utf-8 -*-
"""Verificación final del informe generado."""
import re
from pathlib import Path

INF = Path(r"D:\Escuela\CD\informe")
html = (INF / "index.html").read_text(encoding="utf-8")

tokens = re.findall(r"\{\{[A-Z0-9_]+\}\}", html)
figs = re.findall(r'src="(assets/img/[^"]+)"', html)
dls = sorted(set(re.findall(r'href="(assets/data/[^"]+)"', html)))
ext = re.findall(r'(?:src|href)="https?://[^"]+"', html)

print("marcadores sin reemplazar:", tokens)
print("figuras referenciadas:", len(figs), "| faltan:", [f for f in figs if not (INF / f).exists()])
print("descargas únicas:", len(dls), "| faltan:", [f for f in dls if not (INF / f).exists()])
print("recursos externos:", ext)
print("tamaño index.html:", len(html), "bytes")
print("secciones:", len(re.findall(r'<section class="seccion"', html)))
print("filas del dataset:", len(re.findall(r"<tr data-fuente=", html)))
