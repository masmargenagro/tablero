"""Valida datos-nuevo.json contra datos.json y, si pasa, lo publica en datos.json
y en el respaldo embebido de index.html.

Uso: python3 scripts/actualizar.py datos-nuevo.json
Sale con código 1 y explica el motivo si algo no cierra; en ese caso no toca nada.
"""
import json, re, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
# variación máxima aceptada respecto del valor anterior sin revisión manual
TOPE = {"pizarra": 0.08, "dolar": 0.06, "futuros_a3": 0.08, "futuros_cosecha": 0.08, "hacienda": 0.12, "chicago": 0.06}
# rangos de cordura (unidades del archivo)
RANGO = {"ars_t": (50_000, 3_000_000), "usd_t": (80, 1_200), "tc": (300, 5_000), "ars_kg": (500, 20_000)}

def err(msg):
    print("ERROR:", msg); sys.exit(1)

def dentro(v, r, que):
    if not isinstance(v, (int, float)) or not (RANGO[r][0] <= v <= RANGO[r][1]):
        err(f"{que}: valor fuera de rango ({v})")

def salto(bloque, que, nuevo, viejo):
    if viejo and abs(nuevo / viejo - 1) > TOPE[bloque]:
        err(f"{que}: cambia {nuevo/viejo-1:+.1%} respecto del anterior ({viejo} → {nuevo}); revisar fuente")

def main(ruta):
    nuevo = json.loads(Path(ruta).read_text(encoding="utf-8"))
    viejo = json.loads((RAIZ / "datos.json").read_text(encoding="utf-8"))
    for k in ["actualizado", "actualizado_texto", "pizarra", "dolar", "futuros_a3", "futuros_cosecha", "hacienda", "chicago"]:
        if k not in nuevo: err(f"falta el bloque '{k}'")

    vp = {g["id"]: g for g in viejo["pizarra"]["granos"]}
    for g in nuevo["pizarra"]["granos"]:
        dentro(g["ars"], "ars_t", f"pizarra {g['id']} $"); dentro(g["usd"], "usd_t", f"pizarra {g['id']} US$")
        if g["id"] in vp: salto("pizarra", f"pizarra {g['id']}", g["ars"], vp[g["id"]]["ars"])
        tc = g["ars"] / g["usd"]
        if abs(tc / nuevo["pizarra"]["tc_divisa_bna_comprador"] - 1) > 0.01:
            err(f"pizarra {g['id']}: $ y US$ no son coherentes con el tipo de cambio informado")
    dentro(nuevo["pizarra"]["tc_divisa_bna_comprador"], "tc", "tc divisa")

    vd = {q["id"]: q for q in viejo["dolar"]["cotizaciones"]}
    for q in nuevo["dolar"]["cotizaciones"]:
        dentro(q["venta"], "tc", f"dólar {q['id']}")
        if q["id"] in vd: salto("dolar", f"dólar {q['id']}", q["venta"], vd[q["id"]]["venta"])

    for b in ["futuros_a3", "futuros_cosecha", "chicago"]:
        vb = {(c["grano"], c.get("posicion")): c for c in viejo[b]["contratos"]}
        for c in nuevo[b]["contratos"]:
            if c["usd"] is None and b == "futuros_cosecha":
                continue  # posición sin dato confirmado: la página pide el precio a mano
            dentro(c["usd"], "usd_t", f"{b} {c['grano']} {c.get('posicion')}")
            ant = vb.get((c["grano"], c.get("posicion")))
            if ant and ant.get("usd"):
                salto(b, f"{b} {c['grano']} {c.get('posicion')}", c["usd"], ant["usd"])

    vh = {c["id"]: c for c in viejo["hacienda"]["categorias"]}
    for c in nuevo["hacienda"]["categorias"]:
        dentro(c["ars_kg"], "ars_kg", f"hacienda {c['id']}")
        if c["id"] in vh: salto("hacienda", f"hacienda {c['id']}", c["ars_kg"], vh[c["id"]]["ars_kg"])

    texto = json.dumps(nuevo, ensure_ascii=False, indent=2) + "\n"
    (RAIZ / "datos.json").write_text(texto, encoding="utf-8")
    html = (RAIZ / "index.html").read_text(encoding="utf-8")
    blob = json.dumps(nuevo, ensure_ascii=False, separators=(",", ":"))
    html, n = re.subn(r'(<script id="datos-respaldo" type="application/json">\n).*?(\n</script>)',
                      lambda m: m.group(1) + blob + m.group(2), html, flags=re.S)
    if n != 1: err("no se encontró el bloque de respaldo en index.html")
    (RAIZ / "index.html").write_text(html, encoding="utf-8")
    print("OK: datos validados y publicados")

if __name__ == "__main__":
    if len(sys.argv) != 2: err("uso: python3 scripts/actualizar.py datos-nuevo.json")
    main(sys.argv[1])
