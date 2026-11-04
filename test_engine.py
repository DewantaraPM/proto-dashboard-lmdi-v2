"""Jalankan:  python test_engine.py   (atau: pytest -q)"""
from pathlib import Path

import numpy as np
import pandas as pd

import engine as eg

D = pd.read_csv(Path(__file__).parent / "data_rt_dki.csv")
F = eg.bangun_frame(D)


def test_residual_nol_semua_pasangan_tahun():
    for y in range(2010, 2025):
        h = eg.lmdi_baris(F.loc[y], F.loc[y + 1])
        assert abs(h["residual"]) < 1e-6, (y, h["residual"])


def test_rantai_menjumlah_ke_total():
    h = eg.lmdi_periode(F, 2010, 2025, "rantai")
    assert abs(h["total"] - (F.loc[2025, "C_T"] - F.loc[2010, "C_T"])) < 1e-6
    assert abs(h["residual"]) < 1e-6


def test_hanya_penduduk_berubah():
    r0 = dict(F.loc[2020])
    rt = dict(r0)
    rt["P"] = r0["P"] * 2
    for k in ("PDRB_Konstan_T", "E_L", "E_B", "E_T", "C_L", "C_B", "C_T"):
        rt[k] = r0[k] * 2            # PDRB, energi, emisi ikut 2x => per-kapita tetap
    h = eg.lmdi_baris(r0, rt)
    assert abs(h["pop"] - (rt["C_T"] - r0["C_T"])) < 1e-6
    assert all(abs(h[k]) < 1e-6 for k in ("aff", "int", "mix", "ef"))


def test_bau_tahun_dasar_sama_dengan_data():
    par = eg.tren(F, 2019, 2025)
    r = eg.baris_bau(F.loc[2025], par, 0)
    assert abs(r["C_T"] - F.loc[2025, "C_T"]) < 1e-6


def test_tanpa_tuas_skenario_sama_bau():
    par = eg.tren(F, 2019, 2025)
    p = eg.proyeksi(F.loc[2025], par, 2030)
    assert np.allclose(p["df"]["BAU"], p["df"]["Skenario"])


def test_labelling_persis_target_kali_realisasi():
    par = eg.tren(F, 2019, 2025)
    tgt = list(eg.TARGET_LABEL.values())[0]
    p = eg.proyeksi(F.loc[2025], par, 2030, target=tgt, realisasi=0.5)
    sel = p["df"].iloc[-1]
    assert abs((sel["BAU"] - sel["Skenario"]) - 0.5 * tgt[2030]) < 1e-6
    assert not p["cap_kena"]


def test_atribusi_berurutan_menjumlah_ke_selisih():
    par = eg.tren(F, 2019, 2025)
    tgt = list(eg.TARGET_LABEL.values())[0]
    p = eg.proyeksi(F.loc[2025], par, 2030, target=tgt, realisasi=0.4, cut_grid=0.1,
                    shift_lpg=0.1, eta=0.65)
    sel = p["df"].iloc[-1]
    assert abs(sum(p["atribusi"].values()) - (sel["BAU"] - sel["Skenario"])) < 1e-6


def test_lmdi_proyeksi_residual_nol():
    par = eg.tren(F, 2019, 2025)
    tgt = list(eg.TARGET_LABEL.values())[0]
    p = eg.proyeksi(F.loc[2025], par, 2030, target=tgt, realisasi=1.0, cut_grid=0.2,
                    shift_lpg=0.2)
    h = eg.lmdi_baris(F.loc[2025], p["rows_sim"][-1])
    assert abs(h["residual"]) < 1e-6
    # BAU vs skenario: penduduk & kemakmuran identik => efeknya nol
    hb = eg.lmdi_baris(p["rows_bau"][-1], p["rows_sim"][-1])
    assert abs(hb["pop"]) < 1e-9 and abs(hb["aff"]) < 1e-9


def test_elektrifikasi_naik_emisi_bila_grid_kotor():
    par = eg.tren(F, 2019, 2025)
    p = eg.proyeksi(F.loc[2025], par, 2030, shift_lpg=0.2, eta=0.65)
    assert p["df"].iloc[-1]["Skenario"] > p["df"].iloc[-1]["BAU"]
    ef_impas = eg.ef_impas_elektrifikasi(F.loc[2025, "EF_B"], 0.65)
    assert ef_impas < F.loc[2025, "EF_L"] * eg.KONV_GWH_TJ    # impas < EF grid saat ini


def test_backtest_berjalan():
    det, ring = eg.backtest(F, w=5)
    assert len(det) > 0 and ring["h"].min() == 1
    assert np.isfinite(ring["rmse_mesin"]).all()


if __name__ == "__main__":
    for nama, fn in list(globals().items()):
        if nama.startswith("test_"):
            fn()
            print("OK  ", nama)
    print("\nSemua tes lolos.")
