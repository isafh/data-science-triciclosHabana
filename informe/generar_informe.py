# -*- coding: utf-8 -*-
"""
Genera el informe web (index.html) y todas sus figuras a partir de
dataset_unificado_triciclos.csv.

Uso:  python informe/generar_informe.py
"""

import csv
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

BASE = Path(r"D:\Escuela\CD")
INF = BASE / "informe"
IMG = INF / "assets" / "img"
DAT = INF / "assets" / "data"
IMG.mkdir(parents=True, exist_ok=True)
DAT.mkdir(parents=True, exist_ok=True)
RNG = np.random.default_rng(20261104)

# ------------------------------------------------------------------ estilo
COLORES = {
    "Combustión": "#c2410c",
    "Eléctrico": "#0f766e",
    "Híbrido": "#6d28d9",
    "Panel solar": "#ca8a04",
}
GRIS = "#94a3b8"
TINTA = "#1f2937"
TIPOS = ["Combustión", "Eléctrico", "Híbrido", "Panel solar"]

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.edgecolor": "#d1d5db",
    "axes.labelcolor": TINTA,
    "axes.titlesize": 11.5,
    "axes.titleweight": "bold",
    "axes.titlecolor": TINTA,
    "xtick.color": "#4b5563",
    "ytick.color": "#4b5563",
    "axes.grid": True,
    "grid.color": "#eef2f7",
    "grid.linewidth": .9,
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
    "savefig.bbox": "tight",
})


def limpia(ax, ejes=("top", "right")):
    for e in ejes:
        ax.spines[e].set_visible(False)
    ax.set_axisbelow(True)


def miles(x, dec=0):
    s = f"{x:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def money(x):
    return "$" + miles(x)


# ------------------------------------------------------------------ datos
df = pd.read_csv(BASE / "dataset_unificado_triciclos.csv")
df = df.dropna(subset=["precio_usd", "tipo_propulsion"]).copy()
N = len(df)
FUENTES = ["Libro1", "revolico", "cubancargos"]

# ---------------------------------------------------------------- estadistica
def resumen(g):
    q1, q3 = g.quantile(.25), g.quantile(.75)
    iqr = q3 - q1
    at = g[(g < q1 - 1.5 * iqr) | (g > q3 + 1.5 * iqr)]
    return dict(n=int(g.count()), media=g.mean(), mediana=g.median(), sd=g.std(),
                cv=100 * g.std() / g.mean() if g.mean() else np.nan,
                mn=g.min(), q1=q1, q3=q3, mx=g.max(),
                atipicos=", ".join(money(v) for v in sorted(at)) if len(at) else "—")


EST = {t: resumen(df.loc[df.tipo_propulsion == t, "precio_usd"]) for t in TIPOS}
GLOBAL = resumen(df.precio_usd)


# ---------------------------------------------------------------- contrastes
def kruskal_perm(serie, etiquetas, n_perm=20000):
    v = serie.values.astype(float)
    cats, cnt = np.unique(etiquetas, return_counts=True)
    _, c = np.unique(v, return_counts=True)
    ties = (c ** 3 - c).sum()
    n = len(v)
    corr = 1 - ties / (n ** 3 - n)

    def H(x):
        r = pd.Series(x).rank().values
        tot = sum(r[etiquetas == k].sum() ** 2 / q for k, q in zip(cats, cnt))
        return (12 / (n * (n + 1)) * tot - 3 * (n + 1)) / corr

    obs = H(v)
    null = np.array([H(RNG.permutation(v)) for _ in range(n_perm)])
    return obs, (np.sum(null >= obs) + 1) / (n_perm + 1)


def bf_perm(serie, etiquetas, n_perm=20000):
    v = serie.values.astype(float)
    cats = np.unique(etiquetas)

    def F(x):
        med = {k: np.median(x[etiquetas == k]) for k in cats}
        z = np.abs(x - np.array([med[k] for k in etiquetas]))
        Nn, k = len(z), len(cats)
        g = z.mean()
        num = sum((z[etiquetas == c].mean() - g) ** 2 * (etiquetas == c).sum() for c in cats) / (k - 1)
        den = sum(((z[etiquetas == c] - z[etiquetas == c].mean()) ** 2).sum() for c in cats) / (Nn - k)
        return num / den

    obs = F(v)
    null = np.array([F(RNG.permutation(v)) for _ in range(n_perm)])
    return obs, (np.sum(null >= obs) + 1) / (n_perm + 1)


KW_H, KW_P = kruskal_perm(df.precio_usd, df.tipo_propulsion.values)
BF_F, BF_P = bf_perm(df.precio_usd, df.tipo_propulsion.values)

PARES = []
for i, a in enumerate(TIPOS):
    for b in TIPOS[i + 1:]:
        x = df.loc[df.tipo_propulsion == a, "precio_usd"].values
        y = df.loc[df.tipo_propulsion == b, "precio_usd"].values
        d = np.median(x) - np.median(y)
        pool = np.concatenate([x, y])
        dif = np.array([np.median(p[:len(x)]) - np.median(p[len(x):])
                        for p in (RNG.permutation(pool) for _ in range(20000))])
        PARES.append(dict(a=a, b=b, d=d, p=(np.sum(np.abs(dif) >= abs(d)) + 1) / 20001,
                          na=len(x), nb=len(y)))

# ---------------------------------------------------------------- modelo
FX = 900
SALARIO_CUP = 7442.2
INFLACION_AGO = 25.19
INFLACION_SEP = 28.44
SALARIO_USD = SALARIO_CUP / FX
ESCENARIOS = {
    "Conservador": dict(tarifa=200, pas=20, dias=24, margen=.20),
    "Moderado": dict(tarifa=450, pas=30, dias=26, margen=.15),
    "Favorable": dict(tarifa=650, pas=40, dias=26, margen=.15),
}
ESC = {}
for k, s in ESCENARIOS.items():
    bruto = s["tarifa"] * s["pas"] * s["dias"]
    costos = bruto * s["margen"]
    neto = bruto - costos
    ESC[k] = dict(bruto=bruto, costos=costos, neto=neto, neto_usd=neto / FX,
                  salarios=neto / SALARIO_CUP)

INVERSION = {t: EST[t]["mediana"] for t in TIPOS}
PAYBACK = {t: {k: INVERSION[t] / ESC[k]["neto_usd"] for k in ESC} for t in TIPOS}
ANIOS = {t: INVERSION[t] / SALARIO_USD / 12 for t in TIPOS}
PAYBACK_MIN = min(min(v.values()) for v in PAYBACK.values())
PAYBACK_MAX = max(max(v.values()) for v in PAYBACK.values())

# ---------------------------------------------------------------- tabla helper
def tabla(encabezados, filas, caption="", clases="", alinear=None, pie=None):
    """encabezados: [(texto, 'num'|'txt')] ; filas: list[list[str]]"""
    alinear = alinear or []
    out = [f'<div class="tabla-envoltura">', f'<table class="{clases}">']
    if caption:
        out.append(f"<caption>{caption}</caption>")
    out.append("<thead><tr>")
    for i, (txt, tipo) in enumerate(encabezados):
        cls = ' class="num"' if tipo == "num" else ""
        out.append(f"<th{cls}>{txt}</th>")
    out.append("</tr></thead><tbody>")
    for f in filas:
        out.append("<tr>")
        for i, celda in enumerate(f):
            cls = ' class="num"' if encabezados[i][1] == "num" else ""
            out.append(f"<td{cls}>{celda}</td>")
        out.append("</tr>")
    out.append("</tbody>")
    if pie:
        out.append("<tfoot><tr>" + "".join(f"<td>{c}</td>" for c in pie) + "</tr></tfoot>")
    out.append("</table></div>")
    return "\n".join(out)


# ================================================================== FIGURAS
# 1 · composicion
comp = pd.crosstab(df.fuente, df.tipo_propulsion).reindex(columns=TIPOS, fill_value=0)
comp = comp.reindex([f for f in FUENTES if f in comp.index])
comp.loc["Total"] = comp.sum()
fig, ax = plt.subplots(figsize=(9.6, 4.4))
y = np.arange(len(comp))[::-1]
izq = np.zeros(len(comp))
for t in TIPOS:
    vals = comp[t].values
    ax.barh(y, vals, left=izq, color=COLORES[t], edgecolor="white", height=.62, label=t)
    for yi, v, l in zip(y, vals, izq):
        if v > 0:
            ax.text(l + v / 2, yi, int(v), ha="center", va="center",
                    color="white", fontweight="bold", fontsize=10)
    izq += vals
for yi, tot in zip(y, comp.sum(axis=1)):
    ax.text(tot + .6, yi, f"{int(tot)}", va="center", fontsize=10, color=TINTA, fontweight="bold")
ax.set_yticks(y)
ax.set_yticklabels(comp.index)
ax.set_xlabel("Número de registros")
ax.set_xlim(0, comp.sum(axis=1).max() * 1.12)
ax.legend(ncol=4, frameon=False, loc="lower center", bbox_to_anchor=(.5, 1.02), fontsize=9)
limpia(ax, ("top", "right", "left"))
ax.tick_params(axis="y", length=0)
fig.savefig(IMG / "composicion.png", dpi=170)
plt.close(fig)

# 2 · caja + jitter
fig, ax = plt.subplots(figsize=(9.6, 5.0))
data = [df.loc[df.tipo_propulsion == t, "precio_usd"].values for t in TIPOS]
bp = ax.boxplot(data, patch_artist=True, widths=.5, medianprops=dict(color="white", lw=2.2),
                whiskerprops=dict(color="#6b7280"), capprops=dict(color="#6b7280"),
                flierprops=dict(marker="o", markersize=4, markerfacecolor="#6b7280",
                                markeredgecolor="none", alpha=.6))
for t, box in zip(TIPOS, bp["boxes"]):
    box.set_facecolor(COLORES[t])
    box.set_edgecolor(COLORES[t])
    box.set_alpha(.85)
for i, (t, d) in enumerate(zip(TIPOS, data), start=1):
    ax.scatter(RNG.normal(i, .055, len(d)), d, s=16, color="#111827", alpha=.45, zorder=4,
               linewidths=0)
    ax.text(i, max(d) + 130, f"mediana {money(EST[t]['mediana'])}", ha="center", va="bottom",
            fontsize=9, color=TINTA, fontweight="bold",
            bbox=dict(boxstyle="round,pad=.18", fc="white", ec="#e5e7eb", alpha=.95))
ax.set_xticks(range(1, 5))
ax.set_xticklabels([f"{t}\n(n={EST[t]['n']})" for t in TIPOS])
ax.set_ylabel("Precio (USD)")
ax.set_ylim(3200, 7500)
limpia(ax)
fig.savefig(IMG / "caja_tipos.png", dpi=170)
plt.close(fig)

# 3 · histogramas
fig, axes = plt.subplots(2, 2, figsize=(10, 6.6), sharex=True, sharey=True)
bins = np.arange(3250, 7251, 250)
for ax, t in zip(axes.ravel(), TIPOS):
    d = df.loc[df.tipo_propulsion == t, "precio_usd"]
    ax.hist(d, bins=bins, color=COLORES[t], alpha=.82, edgecolor="white")
    ax.axvline(d.median(), color="#111827", lw=1.6, ls="--")
    ax.text(.03, .93, f"mediana {money(d.median())}", transform=ax.transAxes,
            ha="left", va="top", fontsize=8.5, color="#111827",
            bbox=dict(boxstyle="round,pad=.22", fc="white", ec="#e5e7eb", alpha=.95))
    ax.set_title(f"{t} · n={len(d)}", color=COLORES[t])
    ax.set_yticks([])
    limpia(ax)
    ax.grid(axis="y", visible=False)
for ax in axes[1]:
    ax.set_xlabel("Precio (USD)")
fig.tight_layout()
fig.savefig(IMG / "histograma.png", dpi=170)
plt.close(fig)

# 4 · bandas
cortes = [0, 4000, 4500, 5000, 5500, 6000, 10000]
etiquetas = ["< 4.000", "4.000–4.499", "4.500–4.999", "5.000–5.499", "5.500–5.999", "≥ 6.000"]
colores_banda = ["#dff7f2", "#b7ece2", "#7fdccd", "#3fc4b0", "#159e8d", "#0b6b61"]
matriz = []
for t in TIPOS:
    d = df.loc[df.tipo_propulsion == t, "precio_usd"]
    c = pd.cut(d, bins=cortes, labels=etiquetas, right=False).value_counts().reindex(etiquetas, fill_value=0)
    matriz.append(100 * c / c.sum())
matriz = pd.DataFrame(matriz, index=TIPOS)
fig, ax = plt.subplots(figsize=(10, 4.2))
izq = np.zeros(len(TIPOS))
yy = np.arange(len(TIPOS))[::-1]
for j, e in enumerate(etiquetas):
    vals = matriz[e].values
    ax.barh(yy, vals, left=izq, color=colores_banda[j], edgecolor="white", height=.6,
            label=e)
    for yi, v, l in zip(yy, vals, izq):
        if v >= 8:
            ax.text(l + v / 2, yi, f"{v:.0f}%", ha="center", va="center", fontsize=8.5,
                    color="#0f172a" if j < 4 else "white", fontweight="bold")
    izq += vals
ax.set_yticks(yy)
ax.set_yticklabels(TIPOS)
ax.set_xlim(0, 100)
ax.set_xlabel("Porcentaje de registros del grupo")
ax.legend(ncol=6, frameon=False, fontsize=8, loc="lower center", bbox_to_anchor=(.5, 1.02),
          handlelength=1.1, columnspacing=1.1)
limpia(ax, ("top", "right", "left"))
ax.tick_params(axis="y", length=0)
fig.savefig(IMG / "bandas.png", dpi=170)
plt.close(fig)

# 5 · medianas por fuente
fig, ax = plt.subplots(figsize=(10, 5.0))
ancho = .26
xs = np.arange(len(TIPOS))
for j, f in enumerate(FUENTES):
    vals, ns = [], []
    for t in TIPOS:
        d = df.loc[(df.fuente == f) & (df.tipo_propulsion == t), "precio_usd"]
        vals.append(d.median() if len(d) else np.nan)
        ns.append(len(d))
    pos = xs + (j - 1) * ancho
    bars = ax.bar(pos, vals, width=ancho, color=["#1f2937", "#0f766e", "#ca8a04"][j],
                  alpha=.9, label=f, edgecolor="white")
    for p, v, n in zip(pos, vals, ns):
        if not np.isnan(v):
            ax.text(p, v + 70, f"{money(v)}\nn={n}", ha="center", va="bottom", fontsize=7.6,
                    color=TINTA)
ax.set_xticks(xs)
ax.set_xticklabels(TIPOS)
ax.set_ylabel("Precio mediano (USD)")
ax.set_ylim(0, 6900)
ax.legend(frameon=False, ncol=3, loc="upper right")
limpia(ax)
fig.savefig(IMG / "fuentes.png", dpi=170)
plt.close(fig)

# 6 · municipios
rev = df[df.fuente == "revolico"]
mun = (rev.dropna(subset=["municipio"]).groupby("municipio")["precio_usd"]
       .agg(["count", "median"]).sort_values("median"))
fig, ax = plt.subplots(figsize=(9.2, 4.6))
yy = np.arange(len(mun))
ax.barh(yy, mun["median"], color="#0f766e", alpha=.85, height=.62)
for y, (idx, row) in zip(yy, mun.iterrows()):
    ax.text(row["median"] + 60, y, f"{money(row['median'])}  ·  n={int(row['count'])}",
            va="center", fontsize=8.5, color=TINTA)
ax.set_yticks(yy)
ax.set_yticklabels(mun.index, fontsize=9)
ax.set_xlabel("Precio mediano (USD)")
ax.set_xlim(0, mun["median"].max() * 1.35)
limpia(ax, ("top", "right", "left"))
ax.tick_params(axis="y", length=0)
fig.savefig(IMG / "municipios.png", dpi=170)
plt.close(fig)

# 7 · financiamiento (Libro1)
l1 = df[df.fuente == "Libro1"]
def cuenta(col, orden):
    s = l1[col].fillna("sin dato").str.strip().str.lower()
    m = {"persona a persona": "Persona a persona", "agencia en cuba": "Agencia en Cuba",
         "agencia en eeuu": "Agencia en EE. UU.", "otra": "Otra", "otro": "Otro",
         "autofinanciado": "Autofinanciado", "ayuda exterior": "Ayuda exterior",
         "personal": "Personal", "transporte personas-público": "Pasajeros (público)",
         "transporte de carga": "Carga", "sin dato": "Sin dato"}
    s = s.map(lambda x: m.get(x, x.title()))
    return s.value_counts().reindex([o for o in orden if o in s.values])

paneles = [
    ("Vía de adquisición", cuenta("adquisicion",
     ["Persona a persona", "Agencia en Cuba", "Agencia en EE. UU.", "Otra", "Sin dato"])),
    ("Financiamiento", cuenta("financiamiento",
     ["Ayuda exterior", "Autofinanciado", "Otro", "Sin dato"])),
    ("Uso principal", cuenta("uso",
     ["Pasajeros (público)", "Carga", "Personal", "Otro", "Sin dato"])),
]
fig, axes = plt.subplots(1, 3, figsize=(12, 4.2))
for ax, (tit, s) in zip(axes, paneles):
    yy = np.arange(len(s))[::-1]
    ax.barh(yy, s.values, color="#0f766e", alpha=.85, height=.6)
    for y, v in zip(yy, s.values):
        ax.text(v + .12, y, str(int(v)), va="center", fontsize=9, color=TINTA, fontweight="bold")
    ax.set_yticks(yy)
    ax.set_yticklabels(s.index, fontsize=8.6)
    ax.set_title(tit, fontsize=10)
    ax.set_xlim(0, max(s.values) * 1.25)
    ax.set_xlabel("Registros")
    limpia(ax, ("top", "right", "left"))
    ax.tick_params(axis="y", length=0)
fig.tight_layout()
fig.savefig(IMG / "financiamiento.png", dpi=170)
plt.close(fig)

# 8 · payback
fig, ax = plt.subplots(figsize=(10, 4.8))
escs = ["Conservador", "Moderado", "Favorable"]
colores_e = ["#94a3b8", "#0f766e", "#ca8a04"]
ancho = .25
xs = np.arange(len(TIPOS))
for j, e in enumerate(escs):
    vals = [PAYBACK[t][e] for t in TIPOS]
    pos = xs + (j - 1) * ancho
    ax.bar(pos, vals, width=ancho, color=colores_e[j], label=e, edgecolor="white")
    for p, v in zip(pos, vals):
        ax.text(p, v + 1.2, f"{v:.0f}", ha="center", fontsize=8, color=TINTA)
ax.set_xticks(xs)
ax.set_xticklabels([f"{t}\n{money(INVERSION[t])}" for t in TIPOS], fontsize=9)
ax.set_ylabel("Meses para recuperar la inversión")
ax.set_ylim(0, max(PAYBACK[t][e] for t in TIPOS for e in escs) * 1.14)
ax.legend(frameon=False, ncol=3, loc="upper right", title="Escenario", title_fontsize=9)
limpia(ax)
fig.savefig(IMG / "payback.png", dpi=170)
plt.close(fig)

# 9 · sensibilidad
tarifas = np.arange(100, 1001, 50)
paxes = np.arange(5, 56, 5)
Z = np.array([[INVERSION["Eléctrico"] /
               ((tf * px * 26 * (1 - .15)) / FX) if tf * px > 0 else np.nan
               for tf in tarifas] for px in paxes])
niveles = [3, 6, 9, 12, 15, 18, 21, 24, 30, 36, 45, 60, 90]
fig, ax = plt.subplots(figsize=(9.4, 5.2))
cf = ax.contourf(tarifas, paxes, Z, levels=niveles, cmap="YlOrRd", extend="max")
cs = ax.contour(tarifas, paxes, Z, levels=[6, 12, 18, 24, 36, 60], colors="#0b1220", linewidths=1)
ax.clabel(cs, fmt=lambda v: f"{v:.0f} meses", fontsize=7.5, inline=True)
ax.set_xlabel("Tarifa por pasaje (CUP)")
ax.set_ylabel("Pasajeros por día")
cb = fig.colorbar(cf, ax=ax, pad=.02, ticks=[6, 12, 18, 24, 36, 60])
cb.set_label("Meses de recuperación")
limpia(ax, ())
fig.savefig(IMG / "sensibilidad.png", dpi=170)
plt.close(fig)

# 10 · asequibilidad
fig, ax = plt.subplots(figsize=(8.6, 3.8))
orden = sorted(TIPOS, key=lambda t: ANIOS[t])
yy = np.arange(len(orden))[::-1]
vals = [ANIOS[t] for t in orden]
ax.barh(yy, vals, color=[COLORES[t] for t in orden], alpha=.88, height=.6)
for y, t in zip(yy, orden):
    ax.text(ANIOS[t] + 1, y, f"{miles(ANIOS[t],1)} años", va="center", fontsize=9.5, color=TINTA,
            fontweight="bold")
ax.set_yticks(yy)
ax.set_yticklabels(orden)
ax.set_xlabel("Años de salario medio (ahorro del 100 %)")
ax.set_xlim(0, max(vals) * 1.22)
limpia(ax, ("top", "right", "left"))
ax.tick_params(axis="y", length=0)
fig.savefig(IMG / "asequibilidad.png", dpi=170)
plt.close(fig)

print("Figuras generadas:", len(list(IMG.glob("*.png"))))

# ================================================================== TABLAS
# composicion
filas = []
for f in FUENTES:
    sub = df[df.fuente == f]
    c = sub.tipo_propulsion.value_counts()
    filas.append([f] + [f"{int(c.get(t, 0))} <span class='etiqueta-estado'>({100*c.get(t,0)/len(sub):.1f} %)</span>".replace(".", ",")
                        for t in TIPOS] + [f"<strong>{len(sub)}</strong>"])
c = df.tipo_propulsion.value_counts()
filas.append(["<strong>Total</strong>"] +
             [f"<strong>{int(c.get(t, 0))}</strong> <span class='etiqueta-estado'>({100*c.get(t,0)/N:.1f} %)</span>".replace(".", ",")
              for t in TIPOS] + [f"<strong>{N}</strong>"])
TABLA_COMPOSICION = tabla(
    [("Fuente", "txt")] + [(t, "num") for t in TIPOS] + [("Total", "num")],
    filas, caption="Registros por fuente y tipo de propulsión (porcentaje sobre la fila)")

# cobertura
COB = [
    ("Precio", "ok", "ok", "ok", "Disponible"),
    ("Moneda", "ok", "ok", "ok", "Disponible (USD)"),
    ("Tipo de propulsión", "ok", "ok", "ok", "Disponible"),
    ("Municipio", "ok", "ausente", "ausente", "Parcial"),
    ("Condición (nuevo/usado)", "ok", "ausente", "parcial", "Parcial"),
    ("Vía de adquisición / vendedor", "ausente", "ok", "parcial", "Parcial"),
    ("Financiamiento y plazo", "ausente", "ok", "ausente", "Parcial"),
    ("Marca", "ausente", "ausente", "parcial", "Parcial"),
    ("Modelo", "parcial", "ausente", "ok", "Parcial"),
    ("Año del vehículo", "ausente", "ausente", "ausente", "Ausente"),
    ("Capacidad de carga", "ausente", "ausente", "parcial", "Parcial"),
    ("Descripción / autonomía", "parcial", "ausente", "ok", "Parcial"),
    ("Fecha de publicación", "parcial", "ausente", "ausente", "Ausente"),
]
ICONO = {"ok": '<span class="insignia insignia--ok">Sí</span>',
         "parcial": '<span class="insignia insignia--parcial">Parcial</span>',
         "ausente": '<span class="insignia insignia--gris">No</span>'}
filas = [[v, ICONO[r], ICONO[l], ICONO[c], est] for v, r, l, c, est in COB]
TABLA_COBERTURA = tabla(
    [("Variable", "txt"), ("revolico", "txt"), ("Libro1", "txt"), ("cubancargos", "txt"), ("Cobertura", "txt")],
    filas, caption="Matriz de cobertura de las variables previstas en el diseño metodológico",
    clases="tabla--compacta")

# precios
filas = []
for t in sorted(TIPOS, key=lambda x: -EST[x]["mediana"]):
    e = EST[t]
    filas.append([t, e["n"], f"{100*e['n']/N:.1f} %".replace(".", ","),
                  money(e["media"]), f"<strong>{money(e['mediana'])}</strong>",
                  money(e["sd"]), f"{e['cv']:.1f} %".replace(".", ","),
                  money(e["mn"]), money(e["q1"]), money(e["q3"]), money(e["mx"])])
filas.append(["<strong>Total</strong>", f"<strong>{N}</strong>", "100,0 %", money(GLOBAL["media"]),
              f"<strong>{money(GLOBAL['mediana'])}</strong>", money(GLOBAL["sd"]),
              f"{GLOBAL['cv']:.1f} %".replace(".", ","), money(GLOBAL["mn"]), money(GLOBAL["q1"]),
              money(GLOBAL["q3"]), money(GLOBAL["mx"])])
TABLA_PRECIOS = tabla(
    [("Propulsión", "txt"), ("n", "num"), ("%", "num"), ("Media", "num"), ("Mediana", "num"),
     ("Desv. est.", "num"), ("CV", "num"), ("Mín", "num"), ("Q1", "num"), ("Q3", "num"), ("Máx", "num")],
    filas, caption="Estadísticos de precio (USD) por tipo de propulsión. Datos: 53 registros de tres fuentes")

# test
TABLA_TEST = tabla(
    [("Prueba", "txt"), ("Hipótesis nula", "txt"), ("Estadístico", "num"), ("p", "num"), ("Decisión", "txt")],
    [["Kruskal-Wallis", "Igualdad de distribuciones entre los 4 tipos", f"H = {KW_H:.2f}".replace(".", ","),
      f"{KW_P:.4f}".replace(".", ","), '<span class="insignia insignia--parcial">Se rechaza</span>'],
     ["Brown-Forsythe", "Igualdad de varianzas entre los 4 tipos", f"F = {BF_F:.2f}".replace(".", ","),
      f"{BF_P:.3f}".replace(".", ","), '<span class="insignia insignia--ok">No se rechaza</span>']],
    caption="Contrastes no paramétricos (20.000 permutaciones; corrección por empates en Kruskal-Wallis)",
    clases="tabla--compacta")

# pares
filas = []
for p in sorted(PARES, key=lambda x: x["p"]):
    bonf = '<span class="insignia insignia--ok">Sobrevive</span>' if p["p"] < .0083 else \
           '<span class="insignia insignia--gris">No</span>'
    filas.append([f"{p['a']} vs {p['b']}", money(p["d"]), f"{p['p']:.4f}".replace(".", ","),
                  f"{p['na']} / {p['nb']}", bonf])
TABLA_PARES = tabla(
    [("Par de comparación", "txt"), ("Δ mediana", "num"), ("p", "num"), ("n", "num"), ("Bonferroni (α = 0,0083)", "txt")],
    filas, caption="Diferencias de medianas por pares (permutaciones sobre la diferencia de medianas)",
    clases="tabla--compacta")

# medias por fuente
filas = []
for t in sorted(TIPOS, key=lambda x: -EST[x]["mediana"]):
    fila = [t]
    for f in FUENTES:
        d = df.loc[(df.fuente == f) & (df.tipo_propulsion == t), "precio_usd"]
        fila.append(f"{money(d.median())} <span class='etiqueta-estado'>(n={len(d)})</span>" if len(d) else "—")
    filas.append(fila)
TABLA_MEDIAS_FUENTE = tabla(
    [("Propulsión", "txt")] + [(f, "num") for f in FUENTES], filas,
    caption="Precio mediano por tipo de propulsión y fuente (n entre paréntesis)")

# municipios
mun2 = (rev.dropna(subset=["municipio"]).groupby("municipio")["precio_usd"]
        .agg(n="count", mediana="median", mn="min", mx="max")
        .sort_values("mediana", ascending=False))
con_dato = int(mun2["n"].sum())
filas = [[i, int(r.n), money(r.mediana), money(r.mn), money(r.mx),
          f"{100*r.n/con_dato:.1f} %".replace(".", ",")] for i, r in mun2.iterrows()]
filas.append(["<strong>Sin municipio</strong>", 35 - con_dato, "—", "—", "—", "—"])
TABLA_MUNICIPIOS = tabla(
    [("Municipio", "txt"), ("n", "num"), ("Mediana", "num"), ("Mín", "num"), ("Máx", "num"), ("% con dato", "num")],
    filas, caption="Precios por municipio en los anuncios de revolico (32 de 35 registros con dato)",
    clases="tabla--compacta")

# supuestos
filas = [
    ["Salario medio mensual, La Habana", f"{miles(SALARIO_CUP,1)} CUP", "ONEI", '<span class="insignia insignia--ok">Verificado</span>'],
    ["Tipo de cambio informal", f"{FX} CUP/USD", "El Toque", '<span class="insignia insignia--ok">Verificado</span>'],
    ["Inflación anual", f"{miles(INFLACION_AGO,2)} % (ago.) → {miles(INFLACION_SEP,2)} % (sep. 2026)", "Trading Economics · ONEI", '<span class="insignia insignia--ok">Verificado</span>'],
    ["Salario equivalente en USD", f"${miles(SALARIO_USD, 2)} / mes", "Cálculo propio", "Derivado"],
    ["Tarifa por pasaje", "200 / 450 / 650 CUP", "Conservador / moderado / favorable", "Supuesto"],
    ["Pasajeros por día", "20 / 30 / 40", "Conservador / moderado / favorable", "Supuesto"],
    ["Días trabajados al mes", "24 / 26 / 26", "Conservador / moderado / favorable", "Supuesto"],
    ["Costos operativos", "20 / 15 / 15 %", "Sobre ingreso bruto", "Supuesto"],
    ["Inversión inicial", f"{money(min(INVERSION.values()))}–{money(max(INVERSION.values()))} USD", "Mediana por tipo (sección 05)", "Dato de oferta"],
    ["Ventana de referencia", "60 meses", "Solo para la barra de la calculadora", "Convención"],
]
TABLA_SUPUESTOS = tabla(
    [("Parámetro", "txt"), ("Valor", "txt"), ("Origen", "txt"), ("Estado", "txt")], filas,
    caption="Parámetros del modelo y referencias de contexto", clases="tabla--compacta")

# escenarios
filas = []
for k, e in ESC.items():
    filas.append([k, miles(e["bruto"]), miles(e["costos"]), miles(e["neto"]),
                  money(e["neto_usd"]), f"{e['salarios']:.1f}".replace(".", ",")])
TABLA_ESCENARIOS = tabla(
    [("Escenario", "txt"), ("Ingreso bruto (CUP)", "num"), ("Costos (CUP)", "num"),
     ("Neto (CUP)", "num"), ("Neto (USD)", "num"), ("Salarios/mes", "num")], filas,
    caption="Estado de resultados mensual por escenario operativo")

# payback
filas = []
for t in TIPOS:
    p = PAYBACK[t]
    filas.append([t, money(INVERSION[t]),
                  f"{p['Conservador']:.0f} <span class='etiqueta-estado'>({p['Conservador']/12:.1f} años)</span>".replace(".", ","),
                  f"<strong>{p['Moderado']:.0f}</strong> <span class='etiqueta-estado'>({p['Moderado']/12:.1f} años)</span>".replace(".", ","),
                  f"{p['Favorable']:.0f} <span class='etiqueta-estado'>({p['Favorable']/12:.1f} años)</span>".replace(".", ",")])
TABLA_PAYBACK = tabla(
    [("Propulsión", "txt"), ("Inversión", "num"), ("Conservador", "num"), ("Moderado", "num"), ("Favorable", "num")],
    filas, caption="Meses para recuperar la inversión por tipo y escenario")

# contexto
filas = [
    ["Salario medio mensual, La Habana", f"{miles(SALARIO_CUP,1)} CUP", "ONEI", '<span class="insignia insignia--ok">Verificado</span>'],
    ["Tipo de cambio informal", f"{FX} CUP/USD", "El Toque", '<span class="insignia insignia--ok">Verificado</span>'],
    ["Salario en USD", f"${miles(SALARIO_USD, 2)} / mes", "Cálculo propio", '<span class="insignia insignia--ok">Derivado</span>'],
    ["Precio mediano, eléctrico", money(EST["Eléctrico"]["mediana"]), "Dataset unificado", '<span class="insignia insignia--ok">Verificado</span>'],
    ["Años de salario, eléctrico", f"{ANIOS['Eléctrico']:.1f} años".replace(".", ","), "Cálculo propio", '<span class="insignia insignia--ok">Derivado</span>'],
    ["Inflación anual", f"{miles(INFLACION_AGO,2)} % (ago.) → {miles(INFLACION_SEP,2)} % (sep. 2026)", "Trading Economics · ONEI", '<span class="insignia insignia--ok">Verificado</span>'],
    ["Precio del combustible", "—", "Sin dato", '<span class="insignia insignia--pendiente">Pendiente</span>'],
    ["Remesas recibidas", "—", "Sin dato", '<span class="insignia insignia--pendiente">Pendiente</span>'],
    ["Oferta de transporte público", "—", "Cualitativo", '<span class="insignia insignia--pendiente">Pendiente</span>'],
]
TABLA_CONTEXTO = tabla(
    [("Indicador", "txt"), ("Valor", "num"), ("Fuente", "txt"), ("Estado", "txt")], filas,
    caption="Indicadores de contexto utilizados y pendientes", clases="tabla--compacta")

# dataset
filas = []
for _, r in df.sort_values(["fuente", "tipo_propulsion", "precio_usd"]).iterrows():
    filas.append(
        f'<tr data-fuente="{r.fuente}" data-tipo="{r.tipo_propulsion}">'
        f'<td>{r.fuente}</td><td>{r.id}</td><td>{r.tipo_propulsion}</td>'
        f'<td class="num" data-valor="{r.precio_usd}">{money(r.precio_usd)}</td>'
        f'<td>{"" if pd.isna(r.condicion) else r.condicion}</td>'
        f'<td>{"" if pd.isna(r.municipio) else r.municipio}</td>'
        f'<td>{"" if pd.isna(r.uso) else r.uso}</td>'
        f'<td>{"" if pd.isna(r.adquisicion) else r.adquisicion}</td>'
        f'<td class="num">{"" if pd.isna(r.autonomia_km) else r.autonomia_km}</td>'
        f'<td class="num">{"" if pd.isna(r.capacidad_carga_kg) else int(r.capacidad_carga_kg)}</td>'
        f"</tr>")
FILAS_DATASET = "\n".join(filas)

# KPIs
KPIS = f"""
<div class="kpi"><div class="kpi__valor">{N}</div><div class="kpi__etiqueta">registros de oferta de tres fuentes</div></div>
<div class="kpi"><div class="kpi__valor">${miles(GLOBAL['mediana'])} <small>USD</small></div><div class="kpi__etiqueta">precio mediano · rango ${miles(GLOBAL['mn'])}–${miles(GLOBAL['mx'])}</div></div>
<div class="kpi"><div class="kpi__valor">{100*EST['Eléctrico']['n']/N:.1f} %</div><div class="kpi__etiqueta">de la oferta es eléctrica</div></div>
<div class="kpi"><div class="kpi__valor">{PAYBACK_MIN:.0f}–{PAYBACK_MAX:.0f} <small>meses</small></div><div class="kpi__etiqueta">recuperación estimada según escenario</div></div>
"""

# ---------------------------------------------------------------- reemplazos
REEMPLAZOS = {
    "{{N_TOTAL}}": str(N),
    "{{FECHA_LARGA}}": "4 de noviembre de 2026",
    "{{KPIS}}": KPIS,
    "{{MEDIANA_GLOBAL}}": miles(GLOBAL["mediana"]),
    "{{MIN_GLOBAL}}": miles(GLOBAL["mn"]),
    "{{MAX_GLOBAL}}": miles(GLOBAL["mx"]),
    "{{PCT_ELEC}}": f"{100*EST['Eléctrico']['n']/N:.1f}".replace(".", ","),
    "{{N_ELEC}}": str(EST["Eléctrico"]["n"]),
    "{{CV_ELEC}}": f"{EST['Eléctrico']['cv']:.1f}".replace(".", ","),
    "{{MED_HIB}}": miles(EST["Híbrido"]["mediana"]),
    "{{CV_HIB}}": f"{EST['Híbrido']['cv']:.1f}".replace(".", ","),
    "{{P_VALUE}}": f"{KW_P:.4f}".replace(".", ","),
    "{{MED_COMB}}": miles(EST["Combustión"]["mediana"]),
    "{{MED_SOLAR}}": miles(EST["Panel solar"]["mediana"]),
    "{{MED_ELEC}}": miles(EST["Eléctrico"]["mediana"]),
    "{{MIN_ELEC}}": miles(EST["Eléctrico"]["mn"]),
    "{{MAX_ELEC}}": miles(EST["Eléctrico"]["mx"]),
    "{{Q1_ELEC}}": miles(EST["Eléctrico"]["q1"]),
    "{{Q3_ELEC}}": miles(EST["Eléctrico"]["q3"]),
    "{{MIN_HIB}}": miles(EST["Híbrido"]["mn"]),
    "{{MAX_HIB}}": miles(EST["Híbrido"]["mx"]),
    "{{N_COMB}}": str(EST["Combustión"]["n"]),
    "{{ANIOS_SALARIO_ELEC}}": f"{ANIOS['Eléctrico']:.1f}".replace(".", ","),
    "{{ANIOS_SALARIO_COMB}}": f"{ANIOS['Combustión']:.1f}".replace(".", ","),
    "{{PAYBACK_MIN}}": f"{PAYBACK_MIN:.0f}",
    "{{PAYBACK_MAX}}": f"{PAYBACK_MAX:.0f}",
    "{{PAYBACK_CONS}}": f"{PAYBACK['Eléctrico']['Conservador']:.0f}",
    "{{PAYBACK_MOD}}": f"{PAYBACK['Eléctrico']['Moderado']:.0f}",
    "{{KW_H}}": f"{KW_H:.2f}".replace(".", ","),
    "{{BF_F}}": f"{BF_F:.2f}".replace(".", ","),
    "{{BF_P}}": f"{BF_P:.3f}".replace(".", ","),
    "{{SALARIO}}": miles(SALARIO_CUP, 1),
    "{{FX}}": str(FX),
    "{{PCT_AYUDA}}": f"{100*9/14:.0f}",
    "{{PCT_AGENCIA}}": f"{100*6/14:.0f}",
    "{{MESES_PLAZO}}": "3 años",
    "{{TABLA_COMPOSICION}}": TABLA_COMPOSICION,
    "{{TABLA_COBERTURA}}": TABLA_COBERTURA,
    "{{TABLA_PRECIOS}}": TABLA_PRECIOS,
    "{{TABLA_TEST}}": TABLA_TEST,
    "{{TABLA_PARES}}": TABLA_PARES,
    "{{TABLA_MEDIAS_FUENTE}}": TABLA_MEDIAS_FUENTE,
    "{{TABLA_MUNICIPIOS}}": TABLA_MUNICIPIOS,
    "{{TABLA_SUPUESTOS}}": TABLA_SUPUESTOS,
    "{{TABLA_ESCENARIOS}}": TABLA_ESCENARIOS,
    "{{TABLA_PAYBACK}}": TABLA_PAYBACK,
    "{{TABLA_CONTEXTO}}": TABLA_CONTEXTO,
    "{{FILAS_DATASET}}": FILAS_DATASET,
}

html = (INF / "plantilla.html").read_text(encoding="utf-8")
for k, v in REEMPLAZOS.items():
    html = html.replace(k, str(v))

faltan = [t for t in set(__import__("re").findall(r"\{\{[A-Z0-9_]+\}\}", html))]
if faltan:
    raise SystemExit(f"Marcadores sin reemplazar: {faltan}")

(INF / "index.html").write_text(html, encoding="utf-8")

# ---------------------------------------------------------------- copias
DAT.mkdir(parents=True, exist_ok=True)
for f in ["dataset_unificado_triciclos.csv",
          "catalogo_triciclos_cubancargos.csv",
          "resumen_precios_propulsion_3fuentes.csv"]:
    shutil.copy2(BASE / f, DAT / f)

with open(DAT / "plantilla_entrevistas.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(["id_entrevista", "fecha", "municipio", "rol", "tipo_propulsion",
                "via_compra", "precio_pagado_usd", "forma_pago", "plazo_meses",
                "tenencia", "uso_principal", "pasajeros_dia", "ingreso_mensual_cup",
                "gasto_mensual_cup", "accidentes", "percibe_rentable", "consentimiento"])
    w.writerow(["E001", "", "", "conductor", "", "", "", "", "", "", "", "", "", "", "", "", "sí"])

print("Informe escrito:", INF / "index.html")
print(f"n={N} | KW H={KW_H:.2f} p={KW_P:.4f} | payback {PAYBACK_MIN:.0f}-{PAYBACK_MAX:.0f} meses")
print("Años de salario:", {k: round(v, 1) for k, v in ANIOS.items()})
