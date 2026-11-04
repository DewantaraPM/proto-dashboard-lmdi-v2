"""
engine.py — mesin hitung (tanpa Streamlit/Plotly) agar bisa diuji dan diaudit.

Identitas (dua pembawa energi i = L listrik, B bahan bakar gas [LPG + gas bumi]):
    C = sum_i  P * (Y/P) * (E/Y) * (E_i/E) * (C_i/E_i)

LMDI-I aditif (Ang 2005, 2015). Proyeksi memakai identitas yang SAMA: setiap
faktor diproyeksikan, lalu emisi dihitung ulang dari faktor-faktor tersebut.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

KONV_GWH_TJ = 3.6            # 1 GWh = 3,6 TJ
EF_LPG = 0.06537             # Gg CO2/TJ  (Tier 2 ESDM 2021: 65.370 kg/TJ)
EF_GAS = 0.05764             # Gg CO2/TJ  (Tier 2 ESDM 2021: 57.640 kg/TJ)
EF_LPG_T1 = 0.0631           # Tier 1 IPCC 2006: 63.100 kg/TJ
EF_GAS_T1 = 0.0561           # Tier 1 IPCC 2006: 56.100 kg/TJ

EFEK = ["pop", "aff", "int", "mix", "ef"]
NAMA_EFEK = {
    "pop": "Pertumbuhan penduduk",
    "aff": "Kemakmuran (PDRB/kapita)",
    "int": "Intensitas energi (E/Y)",
    "mix": "Bauran energi (listrik vs bahan bakar gas)",
    "ef": "Faktor emisi",
}

# Target mitigasi rumah tangga (Gg CO2e/tahun) — dua tabel di laporan DLH 2026 TIDAK sama.
TARGET_LABEL = {
    "Tabel 3 — Labelling Program (Ringkasan Eksekutif)": {
        2025: 2442, 2026: 2610, 2027: 2814, 2028: 3054, 2029: 3329, 2030: 3630},
    "Tabel 6.5 — Penerapan Efisiensi Energi RT (Bab 6)": {
        2025: 893, 2026: 1283, 2027: 1721, 2028: 2210, 2029: 2745, 2030: 3322},
}


# ----------------------------------------------------------------------------
# 1. DATA
# ----------------------------------------------------------------------------
def bangun_frame(d: pd.DataFrame, ef_lpg: float = EF_LPG, ef_gas: float = EF_GAS,
                 ef_listrik=None) -> pd.DataFrame:
    """Turunkan konsumsi energi (TJ). Bila GWh_RT_Lapor terisi, pakai data fisik itu."""
    f = d.copy()
    ef_mwh = f["EF_Listrik_tCO2_MWh"].astype(float).to_numpy() if ef_listrik is None \
        else np.asarray(ef_listrik, dtype=float)
    e_l = f["C_Listrik_Gg"].to_numpy(dtype=float) / (ef_mwh / KONV_GWH_TJ)
    if "GWh_RT_Lapor" in f.columns:
        gwh = f["GWh_RT_Lapor"].to_numpy(dtype=float)
        e_l = np.where(np.isnan(gwh), e_l, gwh * KONV_GWH_TJ)
    f["E_L"] = e_l
    f["C_L"] = f["C_Listrik_Gg"].astype(float)
    f["E_B"] = f["C_LPG_Gg"] / ef_lpg + f["C_Gas_Gg"] / ef_gas
    f["C_B"] = (f["C_LPG_Gg"] + f["C_Gas_Gg"]).astype(float)
    f["E_T"] = f["E_L"] + f["E_B"]
    f["C_T"] = f["C_L"] + f["C_B"]
    f["EF_L"] = f["C_L"] / f["E_L"]      # Gg/TJ efektif
    f["EF_B"] = f["C_B"] / f["E_B"]
    f["P"] = f["Penduduk_Juta"].astype(float)
    return f.set_index("Tahun", drop=False)


# ----------------------------------------------------------------------------
# 2. LMDI-I ADITIF
# ----------------------------------------------------------------------------
def log_mean(a: float, b: float) -> float:
    if np.isclose(a, b):
        return float(b)
    return float((a - b) / (np.log(a) - np.log(b)))


def lmdi_baris(r0, rt, aktivitas: str = "PDRB_Konstan_T") -> dict:
    """Dekomposisi dua titik. r0/rt: mapping dengan P, <aktivitas>, E_L, E_B, E_T, C_L, C_B, C_T."""
    P0, Pt = r0["P"], rt["P"]
    Y0, Yt = r0[aktivitas], rt[aktivitas]
    E0, Et = r0["E_T"], rt["E_T"]
    g0, gt = Y0 / P0, Yt / Pt
    I0, It = E0 / Y0, Et / Yt
    out = {k: 0.0 for k in EFEK}
    for i in ("L", "B"):
        c0, ct = r0["C_" + i], rt["C_" + i]
        e0, et = r0["E_" + i], rt["E_" + i]
        L = log_mean(ct, c0)
        out["pop"] += L * np.log(Pt / P0)
        out["aff"] += L * np.log(gt / g0)
        out["int"] += L * np.log(It / I0)
        out["mix"] += L * np.log((et / Et) / (e0 / E0))
        out["ef"] += L * np.log((ct / et) / (c0 / e0))
    out["total"] = float(rt["C_T"] - r0["C_T"])
    out["residual"] = out["total"] - sum(out[k] for k in EFEK)
    return {k: float(v) for k, v in out.items()}


def lmdi_periode(f: pd.DataFrame, a: int, b: int, metode: str = "rantai",
                 aktivitas: str = "PDRB_Konstan_T") -> dict:
    """metode: 'rantai' (jumlah dekomposisi tahunan) atau 'dua titik' (a langsung ke b)."""
    if metode == "dua titik":
        return lmdi_baris(f.loc[a], f.loc[b], aktivitas)
    tot = {k: 0.0 for k in EFEK + ["total", "residual"]}
    for y in range(a, b):
        h = lmdi_baris(f.loc[y], f.loc[y + 1], aktivitas)
        for k in tot:
            tot[k] += h[k]
    return tot


def mc_pembulatan(d: pd.DataFrame, a: int, b: int, n: int = 300, rel: float = 0.005,
                  seed: int = 1, metode: str = "rantai") -> pd.DataFrame:
    """Uji derau: gandakan C_listrik & C_LPG dengan U(1±rel) independen per tahun."""
    rng = np.random.default_rng(seed)
    hasil = []
    for _ in range(n):
        dd = d.copy()
        for col in ("C_Listrik_Gg", "C_LPG_Gg"):
            dd[col] = dd[col] * rng.uniform(1 - rel, 1 + rel, len(dd))
        hasil.append(lmdi_periode(bangun_frame(dd), a, b, metode))
    return pd.DataFrame(hasil)


# ----------------------------------------------------------------------------
# 3. PROYEKSI BERBASIS FAKTOR (identitas yang sama dengan LMDI)
# ----------------------------------------------------------------------------
def tren(f: pd.DataFrame, thn_awal: int, thn_akhir: int, aktivitas: str = "PDRB_Konstan_T") -> dict:
    n = thn_akhir - thn_awal
    r0, r1 = f.loc[thn_awal], f.loc[thn_akhir]
    cagr = lambda x0, x1: (x1 / x0) ** (1.0 / n) - 1.0
    return {
        "r_P": cagr(r0["P"], r1["P"]),
        "r_g": cagr(r0[aktivitas] / r0["P"], r1[aktivitas] / r1["P"]),
        "r_I": cagr(r0["E_T"] / r0[aktivitas], r1["E_T"] / r1[aktivitas]),
        "d_sL": (r1["E_L"] / r1["E_T"] - r0["E_L"] / r0["E_T"]) / n,
    }


def _baris(P, Y, E_L, E_B, EF_L, EF_B) -> dict:
    return {"P": P, "PDRB_Konstan_T": Y, "E_L": E_L, "E_B": E_B, "E_T": E_L + E_B,
            "C_L": E_L * EF_L, "C_B": E_B * EF_B, "C_T": E_L * EF_L + E_B * EF_B}


def baris_bau(base, par: dict, k: int, aktivitas: str = "PDRB_Konstan_T") -> dict:
    """Baseline (tanpa program baru) k tahun setelah tahun dasar."""
    P0, Y0 = base["P"], base[aktivitas]
    g0, I0 = Y0 / P0, base["E_T"] / Y0
    sL0 = base["E_L"] / base["E_T"]
    P = P0 * (1 + par["r_P"]) ** k
    g = g0 * (1 + par["r_g"]) ** k
    Y = P * g
    E = Y * I0 * (1 + par["r_I"]) ** k
    sL = float(np.clip(sL0 + par["d_sL"] * k, 0.01, 0.99))
    return _baris(P, Y, sL * E, (1 - sL) * E, base["EF_L"], base["EF_B"])


def proyeksi(base, par: dict, tahun_akhir: int = 2030, target: dict | None = None,
             realisasi: float = 0.0, cut_grid: float = 0.0, shift_lpg: float = 0.0,
             eta: float = 0.65) -> dict:
    """
    Skenario terhadap baseline. Tuas:
      realisasi : fraksi (0-1) target reduksi (Gg CO2e, dikonversi ke TJ dengan EF listrik tahun dasar)
      cut_grid  : fraksi penurunan EF listrik pada tahun akhir (linear)
      shift_lpg : fraksi energi bahan bakar gas yang berpindah ke listrik pada tahun akhir (linear)
      eta       : energi listrik per energi LPG pada pemakaian akhir (efisiensi relatif; ASUMSI)
    """
    t0 = int(base["Tahun"])
    N = tahun_akhir - t0
    ef_l0, ef_b0 = base["EF_L"], base["EF_B"]
    tahun, c_bau, c_sim, rows_bau, rows_sim = [], [], [], [], []
    cap_kena = False
    for k in range(N + 1):
        rb = baris_bau(base, par, k)
        if k == 0:
            rs = dict(rb)
        else:
            tgt = (target or {}).get(t0 + k, 0.0) * realisasi
            e_l = rb["E_L"] - tgt / ef_l0
            batas = 0.3 * rb["E_L"]
            if e_l < batas:
                e_l, cap_kena = batas, True
            d_b = shift_lpg * (k / N) * rb["E_B"]
            e_b = rb["E_B"] - d_b
            e_l += d_b * eta
            ef_l = ef_l0 * (1 - cut_grid * k / N)
            rs = _baris(rb["P"], rb["PDRB_Konstan_T"], e_l, e_b, ef_l, ef_b0)
        tahun.append(t0 + k)
        c_bau.append(rb["C_T"]); c_sim.append(rs["C_T"])
        rows_bau.append(rb); rows_sim.append(rs)

    # atribusi berurutan (labelling -> elektrifikasi -> grid) pada tahun akhir
    rb, rs = rows_bau[-1], rows_sim[-1]
    tgt = (target or {}).get(tahun_akhir, 0.0) * realisasi
    e_l1 = max(rb["E_L"] - tgt / ef_l0, 0.3 * rb["E_L"])
    c1 = e_l1 * ef_l0 + rb["E_B"] * ef_b0
    d_b = shift_lpg * rb["E_B"]
    c2 = (e_l1 + d_b * eta) * ef_l0 + (rb["E_B"] - d_b) * ef_b0
    atribusi = {"labelling": rb["C_T"] - c1, "elektrifikasi": c1 - c2, "grid": c2 - rs["C_T"]}
    return {
        "df": pd.DataFrame({"Tahun": tahun, "BAU": c_bau, "Skenario": c_sim}),
        "rows_bau": rows_bau, "rows_sim": rows_sim,
        "atribusi": atribusi, "cap_kena": cap_kena,
    }


def ef_impas_elektrifikasi(ef_b: float, eta: float) -> float:
    """EF listrik (tCO2/MWh) di bawah mana pergeseran LPG->listrik menurunkan emisi."""
    return KONV_GWH_TJ * ef_b / eta


# ----------------------------------------------------------------------------
# 4. VALIDASI: BACKTEST ROLLING-ORIGIN
# ----------------------------------------------------------------------------
def ramal_bau(f: pd.DataFrame, origin: int, h: int, w: int = 5) -> float:
    par = tren(f, origin - w, origin)
    return baris_bau(f.loc[origin], par, h)["C_T"]


def backtest(f: pd.DataFrame, w: int = 5, h_max: int = 5) -> tuple[pd.DataFrame, pd.DataFrame]:
    t_min, t_max = int(f["Tahun"].min()), int(f["Tahun"].max())
    baris = []
    for o in range(t_min + w, t_max):
        for h in range(1, min(h_max, t_max - o) + 1):
            akt = f.loc[o + h, "C_T"]
            mesin = ramal_bau(f, o, h, w)
            c_o, c_w = f.loc[o, "C_T"], f.loc[o - w, "C_T"]
            naif_cagr = c_o * (c_o / c_w) ** (h / w)
            baris.append({"origin": o, "h": h, "tahun": o + h, "aktual": akt,
                          "mesin": mesin, "naif_cagr": naif_cagr, "persisten": c_o})
    det = pd.DataFrame(baris)
    for m in ("mesin", "naif_cagr", "persisten"):
        det["err_" + m] = (det[m] / det["aktual"] - 1) * 100
    ring = []
    for h, g in det.groupby("h"):
        r = {"h": h, "n": len(g)}
        for m in ("mesin", "naif_cagr", "persisten"):
            e = g["err_" + m]
            r[f"bias_{m}"] = e.mean()
            r[f"rmse_{m}"] = float(np.sqrt((e ** 2).mean()))
        ring.append(r)
    return det, pd.DataFrame(ring)


def kalibrasi_realisasi(f: pd.DataFrame, target_thn_dasar: float, w: int = 5) -> tuple[float, float]:
    """
    Batas atas realisasi program pada tahun data terakhir: selisih ramalan baseline
    (tren sebelum tahun itu) dengan emisi aktual, dibagi target program tahun itu.
    Selisih ini juga memuat cuaca/perilaku/lainnya, jadi hanya BATAS ATAS.
    """
    t_akhir = int(f["Tahun"].max())
    c_hat = ramal_bau(f, t_akhir - 1, 1, w)
    selisih = c_hat - f.loc[t_akhir, "C_T"]
    if target_thn_dasar <= 0:
        return float(selisih), 0.0
    return float(selisih), float(np.clip(selisih / target_thn_dasar, 0.0, 1.0))
