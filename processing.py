# processing.py
import re
import pandas as pd

# Default dividers (your original values)
DEFAULT_DIVIDERS = [
    ("2×2", 166, 117, 52),
    ("2×4", 166, 57, 52),
    ("3×2", 111, 113, 52),
    ("3×4", 111, 57, 52),
    ("4×2", 82, 115, 52),
    ("4×4", 82, 57, 52),
    ("4×8", 82, 28, 52),
    ("6×4", 52, 56, 30),
]

# Column names expected in the Excel file
COL_STUKLIJST = "Stuklijst"
COL_SOORT = "Soort"
COL_OMSCHR = "Omschrijving"
COL_P = ["P1", "P2", "P3", "P4", "P5"]
COL_NETTO_LEN = "Netto lengte PL"

def cells_count(name: str) -> int:
    m = re.search(r'(\d+)\s*[×xX]\s*(\d+)', str(name))
    if m:
        return int(m.group(1)) * int(m.group(2))
    return 1

def build_dividers_from_rows(rows, height_override=None):
    divs = []
    for r in rows:
        name = str(r["name"])
        L = float(r["L"])
        B = float(r["B"])
        H_raw = float(r["H"])
        H_eff = H_raw if height_override is None else (H_raw if name == "6×4" else height_override)
        divs.append({
            "name": name,
            "L": float(L),
            "B": float(B),
            "H": float(H_eff),
            "cells": cells_count(name),
            "area": float(L) * float(B),
        })
    divs_sorted = sorted(divs, key=lambda d: (-d["cells"], d["area"], d["name"]))
    return divs_sorted

def to_num(x):
    try:
        return float(str(x).replace(",", "."))
    except:
        return 0.0

def detect_shape(soort: str, omschr: str) -> str:
    s = f"{soort or ''} {omschr or ''}".lower()
    if "plaat" in s:
        return "Plaat"
    if "strip" in s and "plat" in s:
        return "Strip/Plat"
    if "vierkant" in s:
        return "Vierkant"
    if "zeskant" in s:
        return "Zeskant"
    if "koker" in s:
        return "Koker"
    if "buis" in s:
        return "Buis"
    if "rond" in s:
        return "Rond"
    return "Onbekend"

def shape_dims(row):
    shape = detect_shape(row.get(COL_SOORT, ""), row.get(COL_OMSCHR, ""))
    p = [to_num(row.get(c, 0)) for c in COL_P]
    p1, p2, p3, p4, p5 = (p + [0,0,0,0,0])[:5]
    length = to_num(row.get(COL_NETTO_LEN, 0))
    if shape == "Plaat":
        L, B, H = p1, p2, p3
    elif shape == "Strip/Plat":
        H, B, L = min(p1, p2), max(p1, p2), length
    elif shape == "Vierkant":
        H, B, L = p1, p1, length
    elif shape == "Zeskant":
        H, B, L = p1, p1, length
    elif shape == "Koker":
        H, B, L = min(p1, p2), max(p1, p2), length
    elif shape == "Buis":
        H, B, L = p1, p1, length
    elif shape == "Rond":
        H, B, L = p1, p1, length
    else:
        H, B, L = p1, p2 if p2 else p1, length if length else max(p1, p2)
    L = 0 if pd.isna(L) else L
    B = 0 if pd.isna(B) else B
    H = 0 if pd.isna(H) else H
    return float(L), float(B), float(H)

def fits(L, B, H, divider: dict) -> bool:
    if H > divider["H"]:
        return False
    Dl, Db = divider["L"], divider["B"]
    return (L <= Dl and B <= Db) or (B <= Dl and L <= Db)

def best_divider(L, B, H, divs: list[dict]):
    for d in divs:
        if fits(L, B, H, d):
            return d["name"]
    return None

def process_df(df_input: pd.DataFrame, dividers_rows=None, height_override_for_95=None) -> pd.DataFrame:
    if dividers_rows is None:
        dividers_rows = [{"name":n,"L":L,"B":B,"H":H} for (n,L,B,H) in DEFAULT_DIVIDERS]

    divs52 = build_dividers_from_rows(dividers_rows, height_override=None)
    divs95 = build_dividers_from_rows(dividers_rows, height_override=height_override_for_95)

    results = []
    for _, row in df_input.iterrows():
        L, B, H = shape_dims(row)
        divider_52 = best_divider(L, B, H, divs52) or "GEEN"
        if divider_52 == "GEEN":
            divider_95 = best_divider(L, B, H, divs95) or "GEEN"
        else:
            divider_95 = best_divider(L, B, H, divs95) or "GEEN"

        reason = ""
        maxL52 = max(d["L"] for d in divs52)
        maxB52 = max(d["B"] for d in divs52)
        if divider_52 == "GEEN":
            if (L > maxL52 or B > maxB52):
                reason = "te groot"
            elif H > 95:
                reason = "te hoog"
            else:
                reason = "past niet"

        results.append({
            "Stuklijst_id": row.get(COL_STUKLIJST, ""),
            "afmetingen (lxbxh) in mm": f"{round(L)}×{round(B)}×{round(H)}",
            "beste indeling (52mm)": divider_52,
            "hoogtecheck 95mm": divider_95,
            "reden": reason
        })

    return pd.DataFrame(results)
