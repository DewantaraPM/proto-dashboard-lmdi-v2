"""
Dashboard hasil magang — Inventarisasi GRK & Capaian Mitigasi DKI Jakarta (data: Laporan Akhir DLH 2026)
Jalankan lokal:  streamlit run app.py
VERSI SATU FILE: data CSV ditanam di dalam file ini, jadi cukup app.py + requirements.txt.
"""
import inspect
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Emisi Jakarta: Seberapa Jauh Kita Sudah Menurunkannya?",
                   page_icon="🌿", layout="wide")

FONT = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
C = {"inventori": "#1E4E79", "baseline": "#C84B31", "reduksi": "#1F8A70", "target": "#D98A3C",
     "abu": "#94A3B8", "gelap": "#1F2937",
     "Transportasi": "#1E4E79", "Energi": "#D98A3C", "Limbah": "#4E9A84", "Kehutanan": "#8E7CC3"}

st.markdown("""
<style>
.block-container { padding-top: 1.8rem; padding-bottom: 3rem; max-width: 1220px; }
.stApp, .stApp p, .stApp li, .stApp label, .stApp td, .stApp th, .stApp h1, .stApp h2, .stApp h3, .stApp h4
 { font-family: Inter, -apple-system, "Segoe UI", Roboto, sans-serif; }
.hero-box { background: linear-gradient(135deg,#0F3443 0%,#1E5F74 60%,#2A8C82 100%); color:#fff; padding:26px 30px;
  border-radius:16px; box-shadow:0 10px 25px rgba(15,52,67,.14); margin-bottom:1.1rem; }
.hero-badge { display:inline-block; background:rgba(255,255,255,.16); color:#E6FFFA; font-size:.78rem; font-weight:600;
  padding:4px 12px; border-radius:999px; letter-spacing:.03em; text-transform:uppercase; margin-bottom:10px; }
.hero-title { font-size:1.8rem; font-weight:700; margin:0 0 6px 0; letter-spacing:-.02em; color:#fff; line-height:1.25; }
.hero-sub { font-size:.97rem; opacity:.92; margin:0; line-height:1.55; max-width:900px; color:#F0FDF4; }
.kpi-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:1.4rem; }
.kpi-card { background:#fff; border:1px solid #E2E8F0; border-radius:14px; padding:16px 18px;
  box-shadow:0 2px 6px rgba(15,23,42,.04); border-top:4px solid #1E4E79; }
.kpi-card.warn { border-top-color:#C84B31; } .kpi-card.good { border-top-color:#1F8A70; } .kpi-card.gold { border-top-color:#D98A3C; }
.kpi-label { font-size:.8rem; color:#64748B; font-weight:500; margin-bottom:4px; }
.kpi-val { font-size:1.55rem; font-weight:700; color:#0F172A; margin-bottom:4px; }
.kpi-delta { font-size:.78rem; font-weight:600; color:#475569; }
.kotak { border-left:4px solid #1E4E79; background:#F8FAFC; border-top:1px solid #E2E8F0; border-right:1px solid #E2E8F0;
  border-bottom:1px solid #E2E8F0; padding:14px 18px; border-radius:0 12px 12px 0; margin:8px 0 18px 0; }
.kotak.hijau { border-left-color:#1F8A70; background:#F0FDF4; }
.kotak.kuning { border-left-color:#D98A3C; background:#FFFBEB; }
.kotak-judul { font-weight:600; color:#0F172A; margin-bottom:4px; font-size:.95rem; }
.sorot { font-size:1.05rem; color:#0F172A; line-height:1.6; background:#fff; border:1px solid #E2E8F0; border-radius:12px;
  padding:14px 18px; margin:6px 0 14px 0; }
button[data-baseweb="tab"] p { font-weight:600; font-size:.94rem; }
#MainMenu, footer { visibility:hidden; }
@media (max-width: 900px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------ utilitas
def fmt(x, d=0):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def jt(ton, d=1):
    """ton -> 'x,y juta ton'"""
    return fmt(ton / 1e6, d)


def tanda(x, d=1):
    return ("+" if x > 0 else "−" if x < 0 else "") + fmt(abs(x), d)


def kotak(judul, isi, warna=""):
    st.markdown(f'<div class="kotak {warna}"><div class="kotak-judul">{judul}</div>'
                f'<div style="font-size:0.92rem;color:#334155;">{isi}</div></div>', unsafe_allow_html=True)


def sorot(isi):
    st.markdown(f'<div class="sorot">{isi}</div>', unsafe_allow_html=True)


def _lebar(fn):
    try:
        return {"width": "stretch"} if "width" in inspect.signature(fn).parameters else {"use_container_width": True}
    except (TypeError, ValueError):
        return {"use_container_width": True}


def tampil(fig):
    st.plotly_chart(fig, config={"displayModeBar": False}, **_lebar(st.plotly_chart))


def tabel(df):
    st.dataframe(df, hide_index=True, **_lebar(st.dataframe))


def gaya(fig, y=None, tinggi=380, x_dtick=None):
    fig.update_layout(template="plotly_white", font=dict(family=FONT, size=12, color="#1E293B"),
                      paper_bgcolor="white", plot_bgcolor="white", margin=dict(l=10, r=10, t=30, b=10), height=tinggi,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title_text=""),
                      yaxis=dict(title=y, gridcolor="#F1F5F9", zerolinecolor="#CBD5E1"), xaxis=dict(showgrid=False))
    if x_dtick:
        fig.update_xaxes(dtick=x_dtick)
    return fig


# ------------------------------------------------------------------ data
# ------------------------------------------------------------------ data (ditanam di dalam file ini)
import io
_CSV = {
    'baseline_inventori': 'tahun,inventori_ton,baseline_ton,reduksi_ton,reduksi_persen,reduksi_kumulatif_persen,pdrb_konstan_rp,intensitas_ton_per_miliar_rp,turun_intensitas_vs_2010_persen,jenis\n2010,40536457.0,40403126.68194956,-133330.31805043668,-0.33000000000000773,-0.33,1080000000000000.0,37.53,-0.0,hasil inventarisasi\n2011,43328066.0,44037062.70962496,708996.709624961,1.6099999999999979,0.6799999999999999,1260000000000000.0,34.39,8.38,hasil inventarisasi\n2012,47980986.0,48033823.205526076,52837.20552607626,0.10999999999999495,0.48,1222527925000000.0,39.25,-4.569999999999999,hasil inventarisasi\n2013,55025819.0,52415525.81444084,-2610293.185559161,-4.980000000000014,-1.0699999999999998,1296694573000000.0,42.44,-13.059999999999999,hasil inventarisasi\n2014,51496907.0,57263323.696208164,5766416.696208164,10.070000000000004,1.5699999999999998,1373389000000000.0,37.5,0.1,hasil inventarisasi\n2015,56610068.0,62580221.092195444,5970153.092195444,9.539999999999997,3.2,1454563850000000.0,38.92,-3.6900000000000004,hasil inventarisasi\n2016,58836848.0,63524992.442237094,4688144.442237094,7.379999999999995,3.92,1539916880000000.0,38.21,-1.7999999999999998,hasil inventarisasi\n2017,57064785.0,64986658.69490946,7921873.694909461,12.189999999999996,5.16,1635359150000000.0,34.89,7.03,hasil inventarisasi\n2018,59963382.0,69193840.29540734,9230458.29540734,13.340000000000002,6.29,1735208290000000.0,34.56,7.93,hasil inventarisasi\n2019,60820113.0,73004576.88152683,12184463.881526828,16.689999999999998,7.61,1836240550000000.0,33.12,11.75,hasil inventarisasi\n2020,54123190.0,73030886.52003779,18907696.520037785,25.89,9.67,1792291090000000.0,30.2,19.55,hasil inventarisasi\n2021,56644278.0,77648084.98971899,21003806.98971899,27.05,11.53,1856000700000000.0,30.52,18.69,hasil inventarisasi\n2022,60264624.0,80892112.75167786,20627488.751677856,25.500000000000007,12.93,1953488990000000.0,30.85,17.810000000000002,hasil inventarisasi\n2023,62620406.0,84576453.26850352,21956047.268503517,25.960000000000004,14.16,2050472970000000.0,30.54,18.63,hasil inventarisasi\n2024,64830985.0,88253450.8576096,23422465.8576096,26.540000000000013,15.28,2151041330000000.0,30.14,19.7,hasil inventarisasi\n2025,66193650.0,91986728.73818788,25793078.73818788,28.04,16.37,2263240000000000.0,29.25,22.08,hasil inventarisasi\n2030,74196000.0,106530000.0,32334000.0,30.352013517319065,,,,,target PerGub 90/2021 (30%)\n',
    'emisi_sektor': 'kode,uraian,tahun,gg_co2e\n1,1. Energi,2010,18822.0\n1,1. Energi,2011,19570.0\n1,1. Energi,2012,21120.0\n1,1. Energi,2013,24023.0\n1,1. Energi,2014,22662.0\n1,1. Energi,2015,25559.0\n1,1. Energi,2016,25781.0\n1,1. Energi,2017,26485.0\n1,1. Energi,2018,28354.0\n1,1. Energi,2019,27665.0\n1,1. Energi,2020,22779.0\n1,1. Energi,2021,24885.0\n1,1. Energi,2022,26715.0\n1,1. Energi,2023,26919.0\n1,1. Energi,2024,27669.0\n1,1. Energi,2025,29311.0\n1A,1A Aktivitas pembakaran bahan bakar,2010,18768.0\n1A,1A Aktivitas pembakaran bahan bakar,2011,19516.0\n1A,1A Aktivitas pembakaran bahan bakar,2012,21066.0\n1A,1A Aktivitas pembakaran bahan bakar,2013,23969.0\n1A,1A Aktivitas pembakaran bahan bakar,2014,22608.0\n1A,1A Aktivitas pembakaran bahan bakar,2015,25505.0\n1A,1A Aktivitas pembakaran bahan bakar,2016,25727.0\n1A,1A Aktivitas pembakaran bahan bakar,2017,26437.0\n1A,1A Aktivitas pembakaran bahan bakar,2018,28312.0\n1A,1A Aktivitas pembakaran bahan bakar,2019,27622.0\n1A,1A Aktivitas pembakaran bahan bakar,2020,22741.0\n1A,1A Aktivitas pembakaran bahan bakar,2021,24855.0\n1A,1A Aktivitas pembakaran bahan bakar,2022,26686.0\n1A,1A Aktivitas pembakaran bahan bakar,2023,26893.0\n1A,1A Aktivitas pembakaran bahan bakar,2024,27644.0\n1A,1A Aktivitas pembakaran bahan bakar,2025,29284.0\n1A1,1A1 Industri energi : Pembangkit listrik,2010,8044.0\n1A1,1A1 Industri energi : Pembangkit listrik,2011,7785.0\n1A1,1A1 Industri energi : Pembangkit listrik,2012,6843.0\n1A1,1A1 Industri energi : Pembangkit listrik,2013,7521.0\n1A1,1A1 Industri energi : Pembangkit listrik,2014,8010.0\n1A1,1A1 Industri energi : Pembangkit listrik,2015,7737.0\n1A1,1A1 Industri energi : Pembangkit listrik,2016,7227.0\n1A1,1A1 Industri energi : Pembangkit listrik,2017,6673.0\n1A1,1A1 Industri energi : Pembangkit listrik,2018,7938.0\n1A1,1A1 Industri energi : Pembangkit listrik,2019,8744.0\n1A1,1A1 Industri energi : Pembangkit listrik,2020,7301.0\n1A1,1A1 Industri energi : Pembangkit listrik,2021,8530.0\n1A1,1A1 Industri energi : Pembangkit listrik,2022,7217.0\n1A1,1A1 Industri energi : Pembangkit listrik,2023,7443.0\n1A1,1A1 Industri energi : Pembangkit listrik,2024,7803.0\n1A1,1A1 Industri energi : Pembangkit listrik,2025,7128.0\n1A2,1A2 Industri Manufaktur,2010,2330.0\n1A2,1A2 Industri Manufaktur,2011,2326.0\n1A2,1A2 Industri Manufaktur,2012,2256.0\n1A2,1A2 Industri Manufaktur,2013,2755.0\n1A2,1A2 Industri Manufaktur,2014,1935.0\n1A2,1A2 Industri Manufaktur,2015,2083.0\n1A2,1A2 Industri Manufaktur,2016,2648.0\n1A2,1A2 Industri Manufaktur,2017,3465.0\n1A2,1A2 Industri Manufaktur,2018,3417.0\n1A2,1A2 Industri Manufaktur,2019,2064.0\n1A2,1A2 Industri Manufaktur,2020,2081.0\n1A2,1A2 Industri Manufaktur,2021,2219.0\n1A2,1A2 Industri Manufaktur,2022,2443.0\n1A2,1A2 Industri Manufaktur,2023,1992.0\n1A2,1A2 Industri Manufaktur,2024,2555.0\n1A2,1A2 Industri Manufaktur,2025,2348.0\n1A3,1A3 Transportasi,2010,7258.0\n1A3,1A3 Transportasi,2011,8201.0\n1A3,1A3 Transportasi,2012,10722.0\n1A3,1A3 Transportasi,2013,12453.0\n1A3,1A3 Transportasi,2014,11424.0\n1A3,1A3 Transportasi,2015,14102.0\n1A3,1A3 Transportasi,2016,14293.0\n1A3,1A3 Transportasi,2017,14671.0\n1A3,1A3 Transportasi,2018,15325.0\n1A3,1A3 Transportasi,2019,15364.0\n1A3,1A3 Transportasi,2020,11903.0\n1A3,1A3 Transportasi,2021,12642.0\n1A3,1A3 Transportasi,2022,15543.0\n1A3,1A3 Transportasi,2023,15992.0\n1A3,1A3 Transportasi,2024,15806.0\n1A3,1A3 Transportasi,2025,18293.0\n1A4,1A4 Lainnya (Komersial dan Residensial),2010,1130.0\n1A4,1A4 Lainnya (Komersial dan Residensial),2011,1198.0\n1A4,1A4 Lainnya (Komersial dan Residensial),2012,1239.0\n1A4,1A4 Lainnya (Komersial dan Residensial),2013,1233.0\n1A4,1A4 Lainnya (Komersial dan Residensial),2014,1233.0\n1A4,1A4 Lainnya (Komersial dan Residensial),2015,1577.0\n1A4,1A4 Lainnya (Komersial dan Residensial),2016,1553.0\n1A4,1A4 Lainnya (Komersial dan Residensial),2017,1622.0\n1A4,1A4 Lainnya (Komersial dan Residensial),2018,1625.0\n1A4,1A4 Lainnya (Komersial dan Residensial),2019,1442.0\n1A4,1A4 Lainnya (Komersial dan Residensial),2020,1450.0\n1A4,1A4 Lainnya (Komersial dan Residensial),2021,1459.0\n1A4,1A4 Lainnya (Komersial dan Residensial),2022,1477.0\n1A4,1A4 Lainnya (Komersial dan Residensial),2023,1458.0\n1A4,1A4 Lainnya (Komersial dan Residensial),2024,1472.0\n1A4,1A4 Lainnya (Komersial dan Residensial),2025,1508.0\n1A5,1A5 Lain,2010,6.0\n1A5,1A5 Lain,2011,6.0\n1A5,1A5 Lain,2012,6.0\n1A5,1A5 Lain,2013,6.0\n1A5,1A5 Lain,2014,6.0\n1A5,1A5 Lain,2015,6.0\n1A5,1A5 Lain,2016,6.0\n1A5,1A5 Lain,2017,6.0\n1A5,1A5 Lain,2018,7.0\n1A5,1A5 Lain,2019,7.0\n1A5,1A5 Lain,2020,6.0\n1A5,1A5 Lain,2021,6.0\n1A5,1A5 Lain,2022,6.0\n1A5,1A5 Lain,2023,7.0\n1A5,1A5 Lain,2024,8.0\n1A5,1A5 Lain,2025,7.0\n1B,1B Emisi fugitive,2010,54.0\n1B,1B Emisi fugitive,2011,54.0\n1B,1B Emisi fugitive,2012,54.0\n1B,1B Emisi fugitive,2013,54.0\n1B,1B Emisi fugitive,2014,54.0\n1B,1B Emisi fugitive,2015,54.0\n1B,1B Emisi fugitive,2016,54.0\n1B,1B Emisi fugitive,2017,48.0\n1B,1B Emisi fugitive,2018,42.0\n1B,1B Emisi fugitive,2019,43.0\n1B,1B Emisi fugitive,2020,38.0\n1B,1B Emisi fugitive,2021,30.0\n1B,1B Emisi fugitive,2022,29.0\n1B,1B Emisi fugitive,2023,25.0\n1B,1B Emisi fugitive,2024,25.0\n1B,1B Emisi fugitive,2025,28.0\n2,2. IPPU,2010,\n2,2. IPPU,2011,\n2,2. IPPU,2012,\n2,2. IPPU,2013,\n2,2. IPPU,2014,\n2,2. IPPU,2015,\n2,2. IPPU,2016,\n2,2. IPPU,2017,\n2,2. IPPU,2018,\n2,2. IPPU,2019,\n2,2. IPPU,2020,\n2,2. IPPU,2021,\n2,2. IPPU,2022,\n2,2. IPPU,2023,\n2,2. IPPU,2024,\n2,2. IPPU,2025,\n3,3. AFOLU,2010,163.0\n3,3. AFOLU,2011,187.0\n3,3. AFOLU,2012,180.0\n3,3. AFOLU,2013,184.0\n3,3. AFOLU,2014,46.0\n3,3. AFOLU,2015,39.0\n3,3. AFOLU,2016,44.0\n3,3. AFOLU,2017,51.0\n3,3. AFOLU,2018,58.0\n3,3. AFOLU,2019,-14.0\n3,3. AFOLU,2020,-29.0\n3,3. AFOLU,2021,38.0\n3,3. AFOLU,2022,-45.0\n3,3. AFOLU,2023,-60.0\n3,3. AFOLU,2024,-51.0\n3,3. AFOLU,2025,-40.0\n3A,3A Peternakan,2010,1.0\n3A,3A Peternakan,2011,1.0\n3A,3A Peternakan,2012,1.0\n3A,3A Peternakan,2013,1.0\n3A,3A Peternakan,2014,1.0\n3A,3A Peternakan,2015,1.0\n3A,3A Peternakan,2016,1.0\n3A,3A Peternakan,2017,1.0\n3A,3A Peternakan,2018,1.0\n3A,3A Peternakan,2019,1.0\n3A,3A Peternakan,2020,1.0\n3A,3A Peternakan,2021,1.0\n3A,3A Peternakan,2022,1.0\n3A,3A Peternakan,2023,1.0\n3A,3A Peternakan,2024,1.0\n3A,3A Peternakan,2025,1.0\n3B,3B Lahan*,2010,160.0\n3B,3B Lahan*,2011,185.0\n3B,3B Lahan*,2012,178.0\n3B,3B Lahan*,2013,182.0\n3B,3B Lahan*,2014,45.0\n3B,3B Lahan*,2015,38.0\n3B,3B Lahan*,2016,43.0\n3B,3B Lahan*,2017,49.0\n3B,3B Lahan*,2018,57.0\n3B,3B Lahan*,2019,-16.0\n3B,3B Lahan*,2020,-31.0\n3B,3B Lahan*,2021,37.0\n3B,3B Lahan*,2022,-46.0\n3B,3B Lahan*,2023,-61.0\n3B,3B Lahan*,2024,-53.0\n3B,3B Lahan*,2025,-41.0\n3C,3C Sumber agregat dan emisi non CO2,2010,2.0\n3C,3C Sumber agregat dan emisi non CO2,2011,1.0\n3C,3C Sumber agregat dan emisi non CO2,2012,2.0\n3C,3C Sumber agregat dan emisi non CO2,2013,1.0\n3C,3C Sumber agregat dan emisi non CO2,2014,1.0\n3C,3C Sumber agregat dan emisi non CO2,2015,1.0\n3C,3C Sumber agregat dan emisi non CO2,2016,1.0\n3C,3C Sumber agregat dan emisi non CO2,2017,1.0\n3C,3C Sumber agregat dan emisi non CO2,2018,1.0\n3C,3C Sumber agregat dan emisi non CO2,2019,1.0\n3C,3C Sumber agregat dan emisi non CO2,2020,1.0\n3C,3C Sumber agregat dan emisi non CO2,2021,1.0\n3C,3C Sumber agregat dan emisi non CO2,2022,0.0\n3C,3C Sumber agregat dan emisi non CO2,2023,0.0\n3C,3C Sumber agregat dan emisi non CO2,2024,0.0\n3C,3C Sumber agregat dan emisi non CO2,2025,0.0\n4,4. Limbah,2010,1873.0\n4,4. Limbah,2011,1837.0\n4,4. Limbah,2012,1746.0\n4,4. Limbah,2013,1845.0\n4,4. Limbah,2014,1915.0\n4,4. Limbah,2015,2000.0\n4,4. Limbah,2016,2083.0\n4,4. Limbah,2017,2199.0\n4,4. Limbah,2018,2284.0\n4,4. Limbah,2019,2305.0\n4,4. Limbah,2020,2396.0\n4,4. Limbah,2021,2450.0\n4,4. Limbah,2022,2478.0\n4,4. Limbah,2023,2369.0\n4,4. Limbah,2024,2362.0\n4,4. Limbah,2025,2444.0\n4A,4A Pengelolaan limbah padat di TPA,2010,941.0\n4A,4A Pengelolaan limbah padat di TPA,2011,892.0\n4A,4A Pengelolaan limbah padat di TPA,2012,791.0\n4A,4A Pengelolaan limbah padat di TPA,2013,886.0\n4A,4A Pengelolaan limbah padat di TPA,2014,941.0\n4A,4A Pengelolaan limbah padat di TPA,2015,1010.0\n4A,4A Pengelolaan limbah padat di TPA,2016,1090.0\n4A,4A Pengelolaan limbah padat di TPA,2017,1167.0\n4A,4A Pengelolaan limbah padat di TPA,2018,1231.0\n4A,4A Pengelolaan limbah padat di TPA,2019,1249.0\n4A,4A Pengelolaan limbah padat di TPA,2020,1336.0\n4A,4A Pengelolaan limbah padat di TPA,2021,1363.0\n4A,4A Pengelolaan limbah padat di TPA,2022,1379.0\n4A,4A Pengelolaan limbah padat di TPA,2023,1296.0\n4A,4A Pengelolaan limbah padat di TPA,2024,1286.0\n4A,4A Pengelolaan limbah padat di TPA,2025,1403.0\n4B,4B Pengelolaan limbah padat secara biologis,2010,\n4B,4B Pengelolaan limbah padat secara biologis,2011,1.1\n4B,4B Pengelolaan limbah padat secara biologis,2012,1.1\n4B,4B Pengelolaan limbah padat secara biologis,2013,1.1\n4B,4B Pengelolaan limbah padat secara biologis,2014,1.1\n4B,4B Pengelolaan limbah padat secara biologis,2015,1.0\n4B,4B Pengelolaan limbah padat secara biologis,2016,1.0\n4B,4B Pengelolaan limbah padat secara biologis,2017,0.0\n4B,4B Pengelolaan limbah padat secara biologis,2018,0.1\n4B,4B Pengelolaan limbah padat secara biologis,2019,0.1\n4B,4B Pengelolaan limbah padat secara biologis,2020,0.1\n4B,4B Pengelolaan limbah padat secara biologis,2021,0.2\n4B,4B Pengelolaan limbah padat secara biologis,2022,0.2\n4B,4B Pengelolaan limbah padat secara biologis,2023,0.4\n4B,4B Pengelolaan limbah padat secara biologis,2024,0.2\n4B,4B Pengelolaan limbah padat secara biologis,2025,0.0\n4C,4C Insinerasi dan pembakaran terbuka,2010,\n4C,4C Insinerasi dan pembakaran terbuka,2011,\n4C,4C Insinerasi dan pembakaran terbuka,2012,\n4C,4C Insinerasi dan pembakaran terbuka,2013,\n4C,4C Insinerasi dan pembakaran terbuka,2014,\n4C,4C Insinerasi dan pembakaran terbuka,2015,\n4C,4C Insinerasi dan pembakaran terbuka,2016,\n4C,4C Insinerasi dan pembakaran terbuka,2017,1.0\n4C,4C Insinerasi dan pembakaran terbuka,2018,1.0\n4C,4C Insinerasi dan pembakaran terbuka,2019,\n4C,4C Insinerasi dan pembakaran terbuka,2020,0.0\n4C,4C Insinerasi dan pembakaran terbuka,2021,1.0\n4C,4C Insinerasi dan pembakaran terbuka,2022,1.0\n4C,4C Insinerasi dan pembakaran terbuka,2023,0.3\n4C,4C Insinerasi dan pembakaran terbuka,2024,0.1\n4C,4C Insinerasi dan pembakaran terbuka,2025,0.3\n4D,4D Pengolahan limbah cair,2010,932.0\n4D,4D Pengolahan limbah cair,2011,944.0\n4D,4D Pengolahan limbah cair,2012,954.0\n4D,4D Pengolahan limbah cair,2013,958.0\n4D,4D Pengolahan limbah cair,2014,973.0\n4D,4D Pengolahan limbah cair,2015,989.0\n4D,4D Pengolahan limbah cair,2016,993.0\n4D,4D Pengolahan limbah cair,2017,1031.0\n4D,4D Pengolahan limbah cair,2018,1051.0\n4D,4D Pengolahan limbah cair,2019,1057.0\n4D,4D Pengolahan limbah cair,2020,1060.0\n4D,4D Pengolahan limbah cair,2021,1086.0\n4D,4D Pengolahan limbah cair,2022,1099.0\n4D,4D Pengolahan limbah cair,2023,1072.0\n4D,4D Pengolahan limbah cair,2024,1076.0\n4D,4D Pengolahan limbah cair,2025,1040.0\nTotal,Total emisi GRK direct,2010,20858.0\nTotal,Total emisi GRK direct,2011,21595.0\nTotal,Total emisi GRK direct,2012,23047.0\nTotal,Total emisi GRK direct,2013,26052.0\nTotal,Total emisi GRK direct,2014,24624.0\nTotal,Total emisi GRK direct,2015,27599.0\nTotal,Total emisi GRK direct,2016,27909.0\nTotal,Total emisi GRK direct,2017,28735.0\nTotal,Total emisi GRK direct,2018,30696.0\nTotal,Total emisi GRK direct,2019,29956.0\nTotal,Total emisi GRK direct,2020,25146.0\nTotal,Total emisi GRK direct,2021,27373.0\nTotal,Total emisi GRK direct,2022,29148.0\nTotal,Total emisi GRK direct,2023,29227.0\nTotal,Total emisi GRK direct,2024,29979.0\nTotal,Total emisi GRK direct,2025,31715.0\nEmisi,Emisi GRK indirect,2010,19733.0\nEmisi,Emisi GRK indirect,2011,21787.0\nEmisi,Emisi GRK indirect,2012,24988.0\nEmisi,Emisi GRK indirect,2013,29028.0\nEmisi,Emisi GRK indirect,2014,26927.0\nEmisi,Emisi GRK indirect,2015,29065.0\nEmisi,Emisi GRK indirect,2016,30982.0\nEmisi,Emisi GRK indirect,2017,28378.0\nEmisi,Emisi GRK indirect,2018,29309.0\nEmisi,Emisi GRK indirect,2019,30907.0\nEmisi,Emisi GRK indirect,2020,29015.0\nEmisi,Emisi GRK indirect,2021,29301.0\nEmisi,Emisi GRK indirect,2022,31145.0\nEmisi,Emisi GRK indirect,2023,33420.0\nEmisi,Emisi GRK indirect,2024,34509.0\nEmisi,Emisi GRK indirect,2025,34507.0\nGrand,Grand total emisi GRK (direct + indirect),2010,40590.0\nGrand,Grand total emisi GRK (direct + indirect),2011,43382.0\nGrand,Grand total emisi GRK (direct + indirect),2012,48035.0\nGrand,Grand total emisi GRK (direct + indirect),2013,55080.0\nGrand,Grand total emisi GRK (direct + indirect),2014,51551.0\nGrand,Grand total emisi GRK (direct + indirect),2015,56664.0\nGrand,Grand total emisi GRK (direct + indirect),2016,58891.0\nGrand,Grand total emisi GRK (direct + indirect),2017,57113.0\nGrand,Grand total emisi GRK (direct + indirect),2018,60005.0\nGrand,Grand total emisi GRK (direct + indirect),2019,60863.0\nGrand,Grand total emisi GRK (direct + indirect),2020,54161.0\nGrand,Grand total emisi GRK (direct + indirect),2021,56674.0\nGrand,Grand total emisi GRK (direct + indirect),2022,60293.0\nGrand,Grand total emisi GRK (direct + indirect),2023,62647.0\nGrand,Grand total emisi GRK (direct + indirect),2024,64488.0\nGrand,Grand total emisi GRK (direct + indirect),2025,66221.0\n',
    'capaian_aksi_2025': 'sektor,aksi,baseline_ton,mitigasi_ton,reduksi_ton,reduksi_persen_aksi\nEnergi,Efisien energi di pembangkit Muara Karang,4197637.0,2936879.0,1260758.0,30.03494585167798\nEnergi,"Penggunaan PLTS rooftop di gedung pemerintahan, sekolah, komersial, industri, rumah tangga dan PLTS komunal",20678.0,0.0,20678.0,100.0\nEnergi,Energi bersih: PLTSa dan pembangkit listrik berbahan bakar LFG,9036.0,847.0,8189.0,90.62638335546703\nEnergi,Substitusi BBM ke gas di Pembangkit Muara Karang dan IP Tanjung Priok,10460482.0,7161905.0,3298577.0,31.533699881133586\nEnergi,Penggunaan biofuel di sub sektor industri,372543.0,225976.0,146566.0,39.34203568447132\nEnergi,Penggunaan biofuel di sub sektor komersial,24280.0,14728.0,9552.0,39.341021416803954\nEnergi,Penerapan green building di gedung pemerintah dan komersial,661638.0,575090.0,86547.0,13.080717854778594\nEnergi,Penggunaan LHE untuk lampu jalan,603905.0,334548.0,269357.0,44.60254510229258\nEnergi,Penggunaan PJU TS,113.0,0.0,113.0,100.0\nEnergi,Pemadaman Listrik berkala,366.0,0.0,366.0,100.0\nTransportasi,Manajemen transportasi melalui penerapan sistem ITS,67670762.0,58883095.0,8787667.0,12.985914064334017\nTransportasi,Busway,451139.0,49028.0,402366.0,89.18891960127588\nTransportasi,Feeder busway,1190711.0,206661.0,966073.0,81.13412910437545\nTransportasi,Penggunaan kereta api Listrik (KRL),245318.0,144691.0,100627.0,41.01900390513538\nTransportasi,Penggunaan MRT,16295.0,6143.0,10153.0,62.30745627493096\nTransportasi,Penggunaan LRT,9843.0,3000.0,6844.0,69.53164685563344\nTransportasi,Penggunaan biofuel,1974534.0,1262427.0,712107.0,36.06456004302787\nTransportasi,Penggunaan BBG,70194.0,56951.0,13243.0,18.866284867652507\nTransportasi,Bus listrik,183134.0,38150.0,144984.0,79.16825930739239\nTransportasi,Car Free Day,7029.0,0.0,7029.0,100.0\nLimbah,LFG Recovery di TPA Bantar Gebang,1574250.0,1537203.0,37352.0,2.3726854057487694\nLimbah,Pengomposan sampah organik,1574250.0,1565718.0,8837.0,0.5613466730188978\nLimbah,Kegiatan 3R kertas,1574250.0,1465372.0,109183.0,6.935556614260759\nLimbah,"PLTSa dan RDF serta Pemanfaatan/ pengolahan lain (maggot, pakan, biodigester, dan sumber energi lainnya)",1574250.0,1558827.0,15727.0,0.9990154041607114\nLimbah,Landfill Mining,1574250.0,1574269.0,285.0,0.01810385898046689\nLimbah,Pengolahan limbah cair on-site (IPAL),1083405.0,1078576.0,4829.0,0.4457243597731227\nLimbah,Pengolahan limbah cair off-site (IPLT),1083405.0,1082747.0,658.0,0.06073444372141536\nKehutanan,Penanaman/ Penghijauan,40967.0,39043.0,1924.0,4.696463006810359\nKehutanan,Konservasi Hutan Mangrove (HL Angke Kapuk),40967.0,34803.0,6164.0,15.046256743232359\n',
    'target_aksi_2025_2030': 'kelompok,sektor,aksi,level,tahun,gg_co2e\nEnergi (Final),Energi (Final),Subtotal Energi (Final),kelompok,2025,12198.0\nEnergi (Final),Energi (Final),Subtotal Energi (Final),kelompok,2026,14268.0\nEnergi (Final),Energi (Final),Subtotal Energi (Final),kelompok,2027,16414.0\nEnergi (Final),Energi (Final),Subtotal Energi (Final),kelompok,2028,18638.0\nEnergi (Final),Energi (Final),Subtotal Energi (Final),kelompok,2029,20943.0\nEnergi (Final),Energi (Final),Subtotal Energi (Final),kelompok,2030,23305.0\nEnergi (Final),Transportasi,Peremajaan dan uji emisi gas buang,aksi,2025,1229.0\nEnergi (Final),Transportasi,Peremajaan dan uji emisi gas buang,aksi,2026,1130.0\nEnergi (Final),Transportasi,Peremajaan dan uji emisi gas buang,aksi,2027,1077.0\nEnergi (Final),Transportasi,Peremajaan dan uji emisi gas buang,aksi,2028,1072.0\nEnergi (Final),Transportasi,Peremajaan dan uji emisi gas buang,aksi,2029,1114.0\nEnergi (Final),Transportasi,Peremajaan dan uji emisi gas buang,aksi,2030,1194.0\nEnergi (Final),Komersial,Green building gedung komersial,aksi,2025,3582.0\nEnergi (Final),Komersial,Green building gedung komersial,aksi,2026,4476.0\nEnergi (Final),Komersial,Green building gedung komersial,aksi,2027,5383.0\nEnergi (Final),Komersial,Green building gedung komersial,aksi,2028,6306.0\nEnergi (Final),Komersial,Green building gedung komersial,aksi,2029,7245.0\nEnergi (Final),Komersial,Green building gedung komersial,aksi,2030,8194.0\nEnergi (Final),Rumah Tangga,"Labelling program (lighting, AC, refrigerasi)",aksi,2025,2442.0\nEnergi (Final),Rumah Tangga,"Labelling program (lighting, AC, refrigerasi)",aksi,2026,2610.0\nEnergi (Final),Rumah Tangga,"Labelling program (lighting, AC, refrigerasi)",aksi,2027,2814.0\nEnergi (Final),Rumah Tangga,"Labelling program (lighting, AC, refrigerasi)",aksi,2028,3054.0\nEnergi (Final),Rumah Tangga,"Labelling program (lighting, AC, refrigerasi)",aksi,2029,3329.0\nEnergi (Final),Rumah Tangga,"Labelling program (lighting, AC, refrigerasi)",aksi,2030,3630.0\nEnergi (Final),Industri,"Boiler, motor listrik, manajer energi",aksi,2025,1282.0\nEnergi (Final),Industri,"Boiler, motor listrik, manajer energi",aksi,2026,1671.0\nEnergi (Final),Industri,"Boiler, motor listrik, manajer energi",aksi,2027,2073.0\nEnergi (Final),Industri,"Boiler, motor listrik, manajer energi",aksi,2028,2490.0\nEnergi (Final),Industri,"Boiler, motor listrik, manajer energi",aksi,2029,2922.0\nEnergi (Final),Industri,"Boiler, motor listrik, manajer energi",aksi,2030,2870.0\nEnergi (Final),Transportasi,Mandatori biofuel di transportasi,aksi,2025,1975.0\nEnergi (Final),Transportasi,Mandatori biofuel di transportasi,aksi,2026,2177.0\nEnergi (Final),Transportasi,Mandatori biofuel di transportasi,aksi,2027,2379.0\nEnergi (Final),Transportasi,Mandatori biofuel di transportasi,aksi,2028,2581.0\nEnergi (Final),Transportasi,Mandatori biofuel di transportasi,aksi,2029,2783.0\nEnergi (Final),Transportasi,Mandatori biofuel di transportasi,aksi,2030,2987.0\nEnergi (Final),Komersial,Mandatori biofuel di komersial,aksi,2025,0.0\nEnergi (Final),Komersial,Mandatori biofuel di komersial,aksi,2026,37.0\nEnergi (Final),Komersial,Mandatori biofuel di komersial,aksi,2027,67.0\nEnergi (Final),Komersial,Mandatori biofuel di komersial,aksi,2028,90.0\nEnergi (Final),Komersial,Mandatori biofuel di komersial,aksi,2029,106.0\nEnergi (Final),Komersial,Mandatori biofuel di komersial,aksi,2030,115.0\nEnergi (Final),Industri,Mandatori biofuel di industri,aksi,2025,346.0\nEnergi (Final),Industri,Mandatori biofuel di industri,aksi,2026,685.0\nEnergi (Final),Industri,Mandatori biofuel di industri,aksi,2027,962.0\nEnergi (Final),Industri,Mandatori biofuel di industri,aksi,2028,1177.0\nEnergi (Final),Industri,Mandatori biofuel di industri,aksi,2029,1331.0\nEnergi (Final),Industri,Mandatori biofuel di industri,aksi,2030,1425.0\nEnergi (Final),Transportasi,BRT (moda shift & elektrifikasi),aksi,2025,811.0\nEnergi (Final),Transportasi,BRT (moda shift & elektrifikasi),aksi,2026,853.0\nEnergi (Final),Transportasi,BRT (moda shift & elektrifikasi),aksi,2027,895.0\nEnergi (Final),Transportasi,BRT (moda shift & elektrifikasi),aksi,2028,938.0\nEnergi (Final),Transportasi,BRT (moda shift & elektrifikasi),aksi,2029,980.0\nEnergi (Final),Transportasi,BRT (moda shift & elektrifikasi),aksi,2030,1024.0\nEnergi (Final),Transportasi,MRT & LRT,aksi,2025,99.0\nEnergi (Final),Transportasi,MRT & LRT,aksi,2026,110.0\nEnergi (Final),Transportasi,MRT & LRT,aksi,2027,122.0\nEnergi (Final),Transportasi,MRT & LRT,aksi,2028,134.0\nEnergi (Final),Transportasi,MRT & LRT,aksi,2029,148.0\nEnergi (Final),Transportasi,MRT & LRT,aksi,2030,162.0\nEnergi (Final),Transportasi,KRL,aksi,2025,176.0\nEnergi (Final),Transportasi,KRL,aksi,2026,202.0\nEnergi (Final),Transportasi,KRL,aksi,2027,229.0\nEnergi (Final),Transportasi,KRL,aksi,2028,257.0\nEnergi (Final),Transportasi,KRL,aksi,2029,285.0\nEnergi (Final),Transportasi,KRL,aksi,2030,315.0\nEnergi (Final),Transportasi,Bahan bakar Euro 4,aksi,2025,6.0\nEnergi (Final),Transportasi,Bahan bakar Euro 4,aksi,2026,12.0\nEnergi (Final),Transportasi,Bahan bakar Euro 4,aksi,2027,18.0\nEnergi (Final),Transportasi,Bahan bakar Euro 4,aksi,2028,23.0\nEnergi (Final),Transportasi,Bahan bakar Euro 4,aksi,2029,27.0\nEnergi (Final),Transportasi,Bahan bakar Euro 4,aksi,2030,31.0\nEnergi (Final),Industri,Jargas untuk industri,aksi,2025,236.0\nEnergi (Final),Industri,Jargas untuk industri,aksi,2026,265.0\nEnergi (Final),Industri,Jargas untuk industri,aksi,2027,295.0\nEnergi (Final),Industri,Jargas untuk industri,aksi,2028,324.0\nEnergi (Final),Industri,Jargas untuk industri,aksi,2029,353.0\nEnergi (Final),Industri,Jargas untuk industri,aksi,2030,878.0\nEnergi (Final),Transportasi,Elektrifikasi transportasi (EV & motor listrik),aksi,2025,0.0\nEnergi (Final),Transportasi,Elektrifikasi transportasi (EV & motor listrik),aksi,2026,20.0\nEnergi (Final),Transportasi,Elektrifikasi transportasi (EV & motor listrik),aksi,2027,72.0\nEnergi (Final),Transportasi,Elektrifikasi transportasi (EV & motor listrik),aksi,2028,157.0\nEnergi (Final),Transportasi,Elektrifikasi transportasi (EV & motor listrik),aksi,2029,275.0\nEnergi (Final),Transportasi,Elektrifikasi transportasi (EV & motor listrik),aksi,2030,427.0\nEnergi (Final),Komersial & Rumah Tangga,PLTS & PLTS rooftop,aksi,2025,13.0\nEnergi (Final),Komersial & Rumah Tangga,PLTS & PLTS rooftop,aksi,2026,21.0\nEnergi (Final),Komersial & Rumah Tangga,PLTS & PLTS rooftop,aksi,2027,28.0\nEnergi (Final),Komersial & Rumah Tangga,PLTS & PLTS rooftop,aksi,2028,36.0\nEnergi (Final),Komersial & Rumah Tangga,PLTS & PLTS rooftop,aksi,2029,44.0\nEnergi (Final),Komersial & Rumah Tangga,PLTS & PLTS rooftop,aksi,2030,51.0\nEnergi (Final),Industri,PLTS rooftop industri,aksi,2025,0.0\nEnergi (Final),Industri,PLTS rooftop industri,aksi,2026,0.0\nEnergi (Final),Industri,PLTS rooftop industri,aksi,2027,0.0\nEnergi (Final),Industri,PLTS rooftop industri,aksi,2028,0.0\nEnergi (Final),Industri,PLTS rooftop industri,aksi,2029,0.0\nEnergi (Final),Industri,PLTS rooftop industri,aksi,2030,5.0\nPembangkit Listrik,Pembangkit Listrik,Subtotal Pembangkit Listrik,kelompok,2025,8471.0\nPembangkit Listrik,Pembangkit Listrik,Subtotal Pembangkit Listrik,kelompok,2026,8251.0\nPembangkit Listrik,Pembangkit Listrik,Subtotal Pembangkit Listrik,kelompok,2027,8546.0\nPembangkit Listrik,Pembangkit Listrik,Subtotal Pembangkit Listrik,kelompok,2028,8775.0\nPembangkit Listrik,Pembangkit Listrik,Subtotal Pembangkit Listrik,kelompok,2029,8995.0\nPembangkit Listrik,Pembangkit Listrik,Subtotal Pembangkit Listrik,kelompok,2030,9170.0\nPembangkit Listrik,Pembangkit Listrik,Efisiensi teknologi pembangkit Muara Karang,aksi,2025,3142.0\nPembangkit Listrik,Pembangkit Listrik,Efisiensi teknologi pembangkit Muara Karang,aksi,2026,3034.0\nPembangkit Listrik,Pembangkit Listrik,Efisiensi teknologi pembangkit Muara Karang,aksi,2027,3129.0\nPembangkit Listrik,Pembangkit Listrik,Efisiensi teknologi pembangkit Muara Karang,aksi,2028,3253.0\nPembangkit Listrik,Pembangkit Listrik,Efisiensi teknologi pembangkit Muara Karang,aksi,2029,3273.0\nPembangkit Listrik,Pembangkit Listrik,Efisiensi teknologi pembangkit Muara Karang,aksi,2030,3381.0\nPembangkit Listrik,Pembangkit Listrik,Fuel switch BBM ke gas Muara Karang,aksi,2025,837.0\nPembangkit Listrik,Pembangkit Listrik,Fuel switch BBM ke gas Muara Karang,aksi,2026,837.0\nPembangkit Listrik,Pembangkit Listrik,Fuel switch BBM ke gas Muara Karang,aksi,2027,837.0\nPembangkit Listrik,Pembangkit Listrik,Fuel switch BBM ke gas Muara Karang,aksi,2028,837.0\nPembangkit Listrik,Pembangkit Listrik,Fuel switch BBM ke gas Muara Karang,aksi,2029,837.0\nPembangkit Listrik,Pembangkit Listrik,Fuel switch BBM ke gas Muara Karang,aksi,2030,837.0\nPembangkit Listrik,Pembangkit Listrik,Fuel switch BBM ke gas Tanjung Priok,aksi,2025,3758.0\nPembangkit Listrik,Pembangkit Listrik,Fuel switch BBM ke gas Tanjung Priok,aksi,2026,3659.0\nPembangkit Listrik,Pembangkit Listrik,Fuel switch BBM ke gas Tanjung Priok,aksi,2027,3746.0\nPembangkit Listrik,Pembangkit Listrik,Fuel switch BBM ke gas Tanjung Priok,aksi,2028,3859.0\nPembangkit Listrik,Pembangkit Listrik,Fuel switch BBM ke gas Tanjung Priok,aksi,2029,3878.0\nPembangkit Listrik,Pembangkit Listrik,Fuel switch BBM ke gas Tanjung Priok,aksi,2030,3977.0\nPembangkit Listrik,Pembangkit Listrik,PLTSa,aksi,2025,492.0\nPembangkit Listrik,Pembangkit Listrik,PLTSa,aksi,2026,480.0\nPembangkit Listrik,Pembangkit Listrik,PLTSa,aksi,2027,596.0\nPembangkit Listrik,Pembangkit Listrik,PLTSa,aksi,2028,589.0\nPembangkit Listrik,Pembangkit Listrik,PLTSa,aksi,2029,731.0\nPembangkit Listrik,Pembangkit Listrik,PLTSa,aksi,2030,739.0\nPembangkit Listrik,Pembangkit Listrik,Pembangkit LFG,aksi,2025,43.0\nPembangkit Listrik,Pembangkit Listrik,Pembangkit LFG,aksi,2026,42.0\nPembangkit Listrik,Pembangkit Listrik,Pembangkit LFG,aksi,2027,39.0\nPembangkit Listrik,Pembangkit Listrik,Pembangkit LFG,aksi,2028,39.0\nPembangkit Listrik,Pembangkit Listrik,Pembangkit LFG,aksi,2029,38.0\nPembangkit Listrik,Pembangkit Listrik,Pembangkit LFG,aksi,2030,39.0\nPembangkit Listrik,Pembangkit Listrik,Biofuel pembangkit tersebar (GBK & komersial),aksi,2025,111.0\nPembangkit Listrik,Pembangkit Listrik,Biofuel pembangkit tersebar (GBK & komersial),aksi,2026,111.0\nPembangkit Listrik,Pembangkit Listrik,Biofuel pembangkit tersebar (GBK & komersial),aksi,2027,111.0\nPembangkit Listrik,Pembangkit Listrik,Biofuel pembangkit tersebar (GBK & komersial),aksi,2028,111.0\nPembangkit Listrik,Pembangkit Listrik,Biofuel pembangkit tersebar (GBK & komersial),aksi,2029,111.0\nPembangkit Listrik,Pembangkit Listrik,Biofuel pembangkit tersebar (GBK & komersial),aksi,2030,111.0\nPembangkit Listrik,Pembangkit Listrik,Biofuel pembangkit tersebar (Kep. Seribu),aksi,2025,87.0\nPembangkit Listrik,Pembangkit Listrik,Biofuel pembangkit tersebar (Kep. Seribu),aksi,2026,87.0\nPembangkit Listrik,Pembangkit Listrik,Biofuel pembangkit tersebar (Kep. Seribu),aksi,2027,87.0\nPembangkit Listrik,Pembangkit Listrik,Biofuel pembangkit tersebar (Kep. Seribu),aksi,2028,87.0\nPembangkit Listrik,Pembangkit Listrik,Biofuel pembangkit tersebar (Kep. Seribu),aksi,2029,87.0\nPembangkit Listrik,Pembangkit Listrik,Biofuel pembangkit tersebar (Kep. Seribu),aksi,2030,87.0\nLimbah,Limbah,Subtotal Limbah,kelompok,2025,416.0\nLimbah,Limbah,Subtotal Limbah,kelompok,2026,632.0\nLimbah,Limbah,Subtotal Limbah,kelompok,2027,803.0\nLimbah,Limbah,Subtotal Limbah,kelompok,2028,1085.0\nLimbah,Limbah,Subtotal Limbah,kelompok,2029,1316.0\nLimbah,Limbah,Subtotal Limbah,kelompok,2030,1598.0\nLimbah,Limbah,Pengomposan,aksi,2025,15.0\nLimbah,Limbah,Pengomposan,aksi,2026,21.0\nLimbah,Limbah,Pengomposan,aksi,2027,26.0\nLimbah,Limbah,Pengomposan,aksi,2028,29.0\nLimbah,Limbah,Pengomposan,aksi,2029,32.0\nLimbah,Limbah,Pengomposan,aksi,2030,34.0\nLimbah,Limbah,Pemanfaatan 3R kertas,aksi,2025,46.0\nLimbah,Limbah,Pemanfaatan 3R kertas,aksi,2026,48.0\nLimbah,Limbah,Pemanfaatan 3R kertas,aksi,2027,49.0\nLimbah,Limbah,Pemanfaatan 3R kertas,aksi,2028,51.0\nLimbah,Limbah,Pemanfaatan 3R kertas,aksi,2029,53.0\nLimbah,Limbah,Pemanfaatan 3R kertas,aksi,2030,55.0\nLimbah,Limbah,Pemanfaatan/pembakaran gas landfill,aksi,2025,87.0\nLimbah,Limbah,Pemanfaatan/pembakaran gas landfill,aksi,2026,101.0\nLimbah,Limbah,Pemanfaatan/pembakaran gas landfill,aksi,2027,117.0\nLimbah,Limbah,Pemanfaatan/pembakaran gas landfill,aksi,2028,135.0\nLimbah,Limbah,Pemanfaatan/pembakaran gas landfill,aksi,2029,157.0\nLimbah,Limbah,Pemanfaatan/pembakaran gas landfill,aksi,2030,182.0\nLimbah,Limbah,PLTSa (limbah padat domestik),aksi,2025,258.0\nLimbah,Limbah,PLTSa (limbah padat domestik),aksi,2026,453.0\nLimbah,Limbah,PLTSa (limbah padat domestik),aksi,2027,601.0\nLimbah,Limbah,PLTSa (limbah padat domestik),aksi,2028,859.0\nLimbah,Limbah,PLTSa (limbah padat domestik),aksi,2029,1065.0\nLimbah,Limbah,PLTSa (limbah padat domestik),aksi,2030,1316.0\nLimbah,Limbah,IPAL terpadu,aksi,2025,9.0\nLimbah,Limbah,IPAL terpadu,aksi,2026,9.0\nLimbah,Limbah,IPAL terpadu,aksi,2027,9.0\nLimbah,Limbah,IPAL terpadu,aksi,2028,10.0\nLimbah,Limbah,IPAL terpadu,aksi,2029,10.0\nLimbah,Limbah,IPAL terpadu,aksi,2030,10.0\nLimbah,Limbah,Kegiatan IPLT,aksi,2025,1.0\nLimbah,Limbah,Kegiatan IPLT,aksi,2026,1.0\nLimbah,Limbah,Kegiatan IPLT,aksi,2027,1.0\nLimbah,Limbah,Kegiatan IPLT,aksi,2028,1.0\nLimbah,Limbah,Kegiatan IPLT,aksi,2029,1.0\nLimbah,Limbah,Kegiatan IPLT,aksi,2030,1.0\nFOLU,FOLU,Peningkatan RTH,kelompok,2025,29.0\nFOLU,FOLU,Peningkatan RTH,kelompok,2026,26.0\nFOLU,FOLU,Peningkatan RTH,kelompok,2027,23.0\nFOLU,FOLU,Peningkatan RTH,kelompok,2028,20.0\nFOLU,FOLU,Peningkatan RTH,kelompok,2029,18.0\nFOLU,FOLU,Peningkatan RTH,kelompok,2030,16.0\nTOTAL,TOTAL,TOTAL,total,2025,21114.0\nTOTAL,TOTAL,TOTAL,total,2026,23178.0\nTOTAL,TOTAL,TOTAL,total,2027,25789.0\nTOTAL,TOTAL,TOTAL,total,2028,28521.0\nTOTAL,TOTAL,TOTAL,total,2029,31235.0\nTOTAL,TOTAL,TOTAL,total,2030,34090.0\n',
    'kategori_kunci_2025': 'kategori,gg_co2e,persen\n1.A.3 Emisi Transportasi,18293.0,58.0\n1.A.1 Emisi Pembangkit Listrik,7128.0,22.0\n1.A.2 Emisi Industri Manufaktur,2348.0,7.0\n4.A.2 Emisi Limbah Padat TPA,1403.0,4.0\n1.A.4.B Emisi Residensial,1391.0,4.0\n4.D.1 Emisi Limbah Cair Domestik,1040.0,3.0\n1.A.4.A Emisi Komersial,117.0,0.0\n1.B.2 Emisi Fugitive Migas,27.8,0.0\n1.A.5 Emisi Lain-lain,7.25,0.0\n',
    'pemeriksaan': 'pemeriksaan,hasil_hitung,acuan_laporan,toleransi,lolos,acuan_sumber\nDirect 2025 = Energi + AFOLU + Limbah,31715.0,31715.0,2.0,True,Tabel 2 Ringkasan\nDirect 2010 = Energi + AFOLU + Limbah,20858.0,20858.0,2.0,True,Tabel 2 Ringkasan\nGrand total 2025 = direct + indirect,66222.0,66221.0,3.0,True,Tabel 2 Ringkasan\nReduksi 2025 (juta ton) = baseline - inventori,25.793,25.8,0.1,True,Gambar 2 / teks Ringkasan\nReduksi 2025 (%),28.04,28.0,0.1,True,teks Ringkasan\nReduksi 2024 (juta ton),23.422,23.4,0.1,True,Gambar 2\nBaseline 2015 (juta ton) cocok dgn label Gambar 2,62.58,63.0,0.6,True,Gambar 2\nBaseline 2016 (juta ton) cocok dgn label Gambar 2,63.525,64.0,0.6,True,Gambar 2\nBaseline 2017 (juta ton) cocok dgn label Gambar 2,64.987,65.0,0.6,True,Gambar 2\nBaseline 2018 (juta ton) cocok dgn label Gambar 2,69.194,69.0,0.6,True,Gambar 2\nBaseline 2019 (juta ton) cocok dgn label Gambar 2,73.005,73.0,0.6,True,Gambar 2\nBaseline 2020 (juta ton) cocok dgn label Gambar 2,73.031,73.0,0.6,True,Gambar 2\nBaseline 2021 (juta ton) cocok dgn label Gambar 2,77.648,78.0,0.6,True,Gambar 2\nBaseline 2022 (juta ton) cocok dgn label Gambar 2,80.892,81.0,0.6,True,Gambar 2\nBaseline 2023 (juta ton) cocok dgn label Gambar 2,84.576,85.0,0.6,True,Gambar 2\nBaseline 2024 (juta ton) cocok dgn label Gambar 2,88.253,88.0,0.6,True,Gambar 2\nBaseline 2025 (juta ton) cocok dgn label Gambar 2,91.987,92.0,0.6,True,Gambar 2\nBaseline 2030 (juta ton),106.53,107.0,0.6,True,Gambar 2 / Tabel 6.1\n"Jumlah aksi sektor Energi+Transportasi (tanpa Car Free Day), ribu ton",16244.767,16245.0,2.0,True,Tabel 5.11\n"Target 2025: jumlah kelompok (Energi, Pembangkit, Limbah, FOLU) = TOTAL (Gg)",21114.0,21114.0,2.0,True,Tabel 3 Ringkasan\n"Target 2030: jumlah kelompok (Energi, Pembangkit, Limbah, FOLU) = TOTAL (Gg)",34089.0,34090.0,3.0,True,Tabel 3 Ringkasan\nTarget 2025: aksi Energi (Final) = subtotalnya (Gg),12197.0,12198.0,3.0,True,Tabel 3 Ringkasan\nTarget 2030: aksi Energi (Final) = subtotalnya (Gg),23308.0,23305.0,3.0,True,Tabel 3 Ringkasan\nTarget 2030 = 32% dari baseline 2030,32.0,32.0,0.2,True,Bab 6.3 (32%)\nTabel 6.3 (Bab VI): \'Energi (Final)\' 2025 vs Tabel 3 (Ringkasan),14903.0,12198.0,2.0,False,dua tabel target berbeda; hanya Tabel 3 yang komponennya menjumlah ke TOTAL\nKategori kunci: 9 terbesar ≈ TOTAL Tabel 5.8 (sisanya kategori kecil & serapan negatif),31755.05,31690.0,70.0,True,Tabel 5.8\n',
}


def _baca(nama):
    return pd.read_csv(io.StringIO(_CSV[nama]))



@st.cache_data
def muat():
    return {
        "bi": _baca("baseline_inventori"),
        "sek": _baca("emisi_sektor"),
        "aksi": _baca("capaian_aksi_2025"),
        "tgt": _baca("target_aksi_2025_2030"),
        "kk": _baca("kategori_kunci_2025"),
        "cek": _baca("pemeriksaan"),
    }


D = muat()
BI = D["bi"]
HIST = BI[BI["jenis"] == "hasil inventarisasi"].set_index("tahun")          # 2010–2025
T_AKHIR = int(HIST.index.max())
T0_CAPAIAN = 2015                                                          # laporan: capaian dihitung sejak 2015
ROW25 = HIST.loc[T_AKHIR]
B2030 = float(BI.loc[BI["tahun"] == 2030, "baseline_ton"].iloc[0])
TARGET_PCT = 32.0                                                           # Bab 6.3 & Tabel 3 (lihat tab Catatan)
TG = D["tgt"]
TOT_TARGET = TG[TG["level"] == "total"].set_index("tahun")["gg_co2e"]       # Gg
T2030_TON = float(TOT_TARGET[2030]) * 1000
# baseline 2026–2029: label pada Gambar 2 laporan (dibulatkan, juta ton)
BASELINE_GRAFIK = {2026: 94, 2027: 98, 2028: 100, 2029: 103}
AKSI = D["aksi"].copy()
TOTAL_AKSI = float(AKSI["reduksi_ton"].sum())

# profil sektor (Gg CO2e)
W = D["sek"].pivot(index="tahun", columns="kode", values="gg_co2e")
SEKTOR = {
    "Transportasi": W["1A3"], "Pembangkit listrik": W["1A1"], "Industri manufaktur": W["1A2"],
    "Rumah tangga & komersial": W["1A4"], "Limbah": W["4"], "Lainnya": W["1A5"].fillna(0) + W["1B"].fillna(0),
}
SEKTOR = pd.DataFrame(SEKTOR) / 1000.0                                      # juta ton
WARNA_SEKTOR = {"Transportasi": "#1E4E79", "Pembangkit listrik": "#D98A3C", "Industri manufaktur": "#8E7CC3",
                "Rumah tangga & komersial": "#4E9A84", "Limbah": "#C84B31", "Lainnya": "#94A3B8"}

# penjelasan awam tiap aksi (ditulis penyusun dashboard dari nama aksi; mohon diverifikasi dengan DLH)
DESKRIPSI = [
    ("plts rooftop", "Panel surya di atap gedung pemerintah, sekolah, komersial, industri, dan rumah tangga menggantikan sebagian listrik dari jaringan."),
    ("pltsa dan pembangkit", "Listrik dihasilkan dari pengolahan sampah (PLTSa) dan gas dari timbunan sampah (LFG)."),
    ("substitusi bbm", "Pembangkit beralih dari bahan bakar minyak ke gas, yang menghasilkan emisi lebih rendah untuk energi yang sama."),
    ("muara karang", "Pembangkit listrik Muara Karang beralih teknologi (dari PLTG ke PLTGU) sehingga listrik yang sama dihasilkan dengan bahan bakar lebih sedikit."),
    ("biofuel di sub sektor", "Sebagian bahan bakar fosil diganti bahan bakar nabati (biofuel)."),
    ("green building", "Gedung pemerintah dan komersial dibangun/dikelola agar lebih hemat energi."),
    ("lhe", "Lampu jalan diganti jenis hemat energi sehingga memakai lebih sedikit listrik."),
    ("pju ts", "Penerangan jalan umum bertenaga surya."),
    ("pemadaman listrik", "Pemadaman listrik berkala sehingga pemakaian listrik berkurang."),
    ("its", "Sistem lalu lintas cerdas mengatur lampu lalu lintas agar kendaraan tidak terlalu lama berhenti dan bahan bakar tidak terbuang."),
    ("feeder", "Angkutan pengumpan menuju busway mengajak warga meninggalkan kendaraan pribadi."),
    ("busway", "Warga beralih dari kendaraan pribadi ke busway (TransJakarta)."),
    ("kereta api listrik", "Penumpang memakai KRL, bukan kendaraan pribadi."),
    ("mrt", "Penumpang memakai MRT, bukan kendaraan pribadi."),
    ("lrt", "Penumpang memakai LRT, bukan kendaraan pribadi."),
    ("penggunaan biofuel", "BBM kendaraan dicampur bahan bakar nabati (mis. biodiesel)."),
    ("bbg", "Kendaraan umum dan operasional memakai bahan bakar gas."),
    ("bus listrik", "Bus listrik menggantikan bus berbahan bakar minyak."),
    ("car free day", "Hari bebas kendaraan bermotor mengurangi pemakaian kendaraan pada hari tertentu."),
    ("lfg recovery", "Gas metana dari timbunan sampah di TPA Bantar Gebang ditangkap dan dimanfaatkan atau dibakar."),
    ("pengomposan", "Sampah organik diolah menjadi kompos sehingga tidak menumpuk di TPA."),
    ("3r kertas", "Kertas dikurangi, dipakai ulang, dan didaur ulang."),
    ("pltsa dan rdf", "Sampah diolah menjadi energi atau dimanfaatkan lain (pakan, maggot, biodigester)."),
    ("landfill mining", "Timbunan sampah lama digali kembali untuk dimanfaatkan."),
    ("on-site", "Limbah cair domestik diolah di tempat (instalasi pengolahan air limbah)."),
    ("off-site", "Lumpur tinja diolah di instalasi pengolahan lumpur tinja."),
    ("penghijauan", "Penanaman pohon menyerap karbon dioksida dari udara."),
    ("mangrove", "Hutan mangrove dilindungi karena menyerap dan menyimpan karbon."),
]


def deskripsi(nama):
    n = nama.lower()
    for kunci, teks in DESKRIPSI:
        if kunci in n:
            return teks
    return "Penjelasan belum tersedia."


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown("### 🌿 Hasil Magang")
    st.caption("**Inventarisasi GRK dan Capaian Mitigasi DKI Jakarta**  \nDisusun oleh: Dewantara Putra Makmur  \n"
               "Departemen Geofisika dan Meteorologi, IPB University")
    st.divider()
    st.caption("**Sumber data:** Laporan Akhir Inventarisasi dan Pengendalian Emisi GRK Provinsi DKI Jakarta 2026 (DLH). "
               "Semua angka di dashboard berasal dari tabel laporan; yang dihitung ulang dijelaskan di tab *Catatan*.")
    st.caption("Satuan utama: **juta ton CO₂e** (karbon dioksida ekuivalen).")

# ------------------------------------------------------------------ hero + kpi
c25 = float(ROW25["inventori_ton"])
c10 = float(HIST.loc[2010, "inventori_ton"])
st.markdown("""
<div class="hero-box">
  <div class="hero-badge">Hasil Magang · Inventarisasi GRK DKI Jakarta</div>
  <div class="hero-title">Seberapa Jauh Jakarta Sudah Menurunkan Emisinya?</div>
  <div class="hero-sub">Penjelasan sederhana tentang hasil inventarisasi gas rumah kaca Jakarta 2010–2025:
  dari mana emisinya, apa yang sudah dilakukan, dan ke mana targetnya.</div>
</div>
""", unsafe_allow_html=True)
st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-card warn"><div class="kpi-label">Emisi Jakarta {T_AKHIR}</div>
    <div class="kpi-val">{jt(c25)} juta ton</div>
    <div class="kpi-delta">{tanda((c25 / c10 - 1) * 100, 0)}% dibanding 2010</div></div>
  <div class="kpi-card good"><div class="kpi-label">Penurunan vs. skenario tanpa aksi ({T_AKHIR})</div>
    <div class="kpi-val">{jt(ROW25['reduksi_ton'])} juta ton</div>
    <div class="kpi-delta">{fmt(ROW25['reduksi_persen'], 1)}% di bawah baseline</div></div>
  <div class="kpi-card gold"><div class="kpi-label">Emisi per rupiah ekonomi</div>
    <div class="kpi-val">−{fmt(ROW25['turun_intensitas_vs_2010_persen'], 0)}%</div>
    <div class="kpi-delta">intensitas emisi {T_AKHIR} vs. 2010</div></div>
  <div class="kpi-card"><div class="kpi-label">Target penurunan 2030</div>
    <div class="kpi-val">{fmt(TARGET_PCT, 0)}%</div>
    <div class="kpi-delta">≈ {jt(T2030_TON)} juta ton dari baseline</div></div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏠 Gambaran Besar", "🏭 Dari Mana Emisinya?", "✅ Apa yang Sudah Dilakukan?",
                                        "🎯 Mau ke Mana?", "📎 Catatan & Sumber"])

# ================================================================== TAB 1
with tab1:
    kotak("Tahukah kamu?",
          "Untuk tahu apakah sebuah kota berhasil menurunkan emisi, kita butuh pembanding. Bayangkan emisi seperti pengeluaran bulanan: "
          "<b>baseline</b> adalah pengeluaran yang <i>akan terjadi</i> kalau kebiasaan dibiarkan (hanya perkiraan), "
          "<b>inventori</b> adalah pengeluaran yang <i>benar-benar terjadi</i>, dan selisihnya adalah &lsquo;penghematan&rsquo; yang diklaim "
          "sebagai hasil program mitigasi. <br><b>Perhatikan:</b> &lsquo;turun&rsquo; di sini berarti <i>lebih rendah dari baseline</i>. "
          f"Emisi Jakarta yang sebenarnya {fmt((c25 / c10 - 1) * 100, 0)}% lebih tinggi daripada 2010; yang berhasil ditekan adalah lajunya.", "hijau")

    th = st.slider("Pilih tahun untuk melihat perbandingannya", T0_CAPAIAN, T_AKHIR, T_AKHIR, key="th_beranda")
    r = HIST.loc[th]
    sorot(f"Pada <b>{th}</b>, tanpa aksi mitigasi Jakarta diperkirakan mengeluarkan <b>{jt(r['baseline_ton'])} juta ton</b> CO₂e. "
          f"Kenyataannya <b>{jt(r['inventori_ton'])} juta ton</b>. Selisihnya <b style='color:#1F8A70'>{jt(r['reduksi_ton'])} juta ton "
          f"({fmt(r['reduksi_persen'], 1)}%)</b> dianggap sebagai penurunan.")

    h = HIST.loc[T0_CAPAIAN:]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=h.index, y=h["baseline_ton"] / 1e6, name="Baseline: perkiraan tanpa aksi", mode="lines",
                             line=dict(color=C["baseline"], width=2.5, dash="dash"),
                             hovertemplate="%{x}: tanpa aksi, emisi diperkirakan %{y:.1f} juta ton<extra></extra>"))
    fig.add_trace(go.Scatter(x=h.index, y=h["inventori_ton"] / 1e6, name="Inventori: emisi sebenarnya", mode="lines+markers",
                             line=dict(color=C["inventori"], width=3), fill="tonexty", fillcolor="rgba(31,138,112,0.16)",
                             hovertemplate="%{x}: emisi sebenarnya %{y:.1f} juta ton<extra></extra>"))
    fig.add_shape(type="line", x0=th, x1=th, y0=r["inventori_ton"] / 1e6, y1=r["baseline_ton"] / 1e6,
                  line=dict(color=C["reduksi"], width=5))
    fig.add_annotation(x=th, y=(r["inventori_ton"] + r["baseline_ton"]) / 2e6, text=f"  Penurunan {jt(r['reduksi_ton'])} juta ton",
                       showarrow=False, xanchor="left", font=dict(color=C["reduksi"], size=13))
    fig.update_xaxes(range=[T0_CAPAIAN - 0.5, T_AKHIR + 3.2])
    tampil(gaya(fig, "Juta ton CO₂e", 400, 1))
    st.caption("Area hijau = selisih baseline dan inventori. Baseline dihitung laporan dari tahun dasar 2010 dengan asumsi tidak ada aksi mitigasi.")

    st.markdown("**Ekonomi tumbuh lebih cepat daripada emisinya**")
    idx = HIST.copy()
    e_idx = idx["inventori_ton"] / idx.loc[2010, "inventori_ton"] * 100
    p_idx = idx["pdrb_konstan_rp"] / idx.loc[2010, "pdrb_konstan_rp"] * 100
    f2 = go.Figure()
    f2.add_trace(go.Scatter(x=idx.index, y=p_idx, name="Ukuran ekonomi (PDRB harga konstan)", mode="lines",
                            line=dict(color=C["target"], width=3),
                            hovertemplate="%{x}: ekonomi = %{y:.0f} (2010 = 100)<extra></extra>"))
    f2.add_trace(go.Scatter(x=idx.index, y=e_idx, name="Emisi GRK", mode="lines", line=dict(color=C["inventori"], width=3),
                            hovertemplate="%{x}: emisi = %{y:.0f} (2010 = 100)<extra></extra>"))
    tampil(gaya(f2, "Indeks (2010 = 100)", 330, 1))
    sorot(f"Sejak 2010, ekonomi Jakarta tumbuh sekitar <b>{fmt(p_idx[T_AKHIR] - 100, 0)}%</b>, sedangkan emisinya naik sekitar "
          f"<b>{fmt(e_idx[T_AKHIR] - 100, 0)}%</b>. Artinya emisi yang dilepas untuk setiap rupiah kegiatan ekonomi turun: dari "
          f"<b>{fmt(HIST.loc[2010, 'intensitas_ton_per_miliar_rp'], 1)}</b> menjadi <b>{fmt(ROW25['intensitas_ton_per_miliar_rp'], 1)}</b> "
          "ton CO₂e per Rp 1 miliar PDRB.")

    with st.expander("📖 Istilah yang sering muncul"):
        st.markdown("""
- **GRK (gas rumah kaca):** gas yang menahan panas di atmosfer, terutama karbon dioksida (CO₂) dan metana (CH₄).
- **CO₂e (ekuivalen):** satuan gabungan; semua gas dinyatakan setara jumlah CO₂ agar bisa dijumlahkan.
- **Inventarisasi:** perhitungan resmi emisi yang benar-benar terjadi pada satu tahun.
- **Baseline:** perkiraan emisi jika tidak ada aksi mitigasi apa pun.
- **Mitigasi:** tindakan untuk mengurangi emisi, misalnya angkutan umum, efisiensi listrik, dan pengolahan sampah.
- **PDRB:** ukuran besarnya kegiatan ekonomi di Jakarta.
""")

# ================================================================== TAB 2
with tab2:
    st.subheader("Dari Mana Emisi Jakarta Berasal?")
    c1, c2 = st.columns([3, 2])
    with c1:
        ths = st.slider("Pilih tahun", 2010, T_AKHIR, T_AKHIR, key="th_sektor")
    with c2:
        mode = st.radio("Tampilkan sebagai", ["Juta ton", "Persen"], horizontal=True)
    s = SEKTOR.loc[ths].sort_values()
    tot_s = float(s.sum())
    nilai = s if mode == "Juta ton" else s / tot_s * 100
    fig = go.Figure(go.Bar(
        x=nilai.values, y=nilai.index, orientation="h", marker_color=[WARNA_SEKTOR[k] for k in nilai.index],
        text=[f"{fmt(v, 1)} {'juta ton' if mode == 'Juta ton' else '%'}" for v in nilai.values], textposition="outside",
        cliponaxis=False,
        customdata=np.stack([s.values, s.values / tot_s * 100], axis=1),
        hovertemplate="%{y} menyumbang %{customdata[0]:.1f} juta ton (%{customdata[1]:.0f}% dari emisi langsung)<extra></extra>"))
    fig = gaya(fig, None, 340)
    fig.update_xaxes(title="Juta ton CO₂e" if mode == "Juta ton" else "% dari emisi langsung",
                     range=[0, float(nilai.max()) * 1.25], showgrid=True, gridcolor="#F1F5F9")
    fig.update_yaxes(title=None)
    tampil(fig)
    teratas = s.idxmax()
    sorot(f"Pada <b>{ths}</b>, sektor terbesar adalah <b>{teratas}</b>: <b>{fmt(s.max(), 1)} juta ton</b> atau "
          f"<b>{fmt(s.max() / tot_s * 100, 0)}%</b> dari {fmt(tot_s, 1)} juta ton emisi langsung sektor energi dan limbah.")

    st.markdown("**Lihat tren satu sektor**")
    pilih = st.selectbox("Pilih sektor", list(SEKTOR.columns), index=0)
    ser = SEKTOR[pilih]
    f3 = go.Figure()
    f3.add_trace(go.Scatter(x=ser.index, y=ser.values, mode="lines+markers", line=dict(color=WARNA_SEKTOR[pilih], width=3),
                            hovertemplate="%{x}: " + pilih + " = %{y:.1f} juta ton<extra></extra>", name=pilih))
    f3.add_trace(go.Scatter(x=[ths], y=[ser[ths]], mode="markers", marker=dict(size=14, color=C["gelap"]), name="Tahun terpilih",
                            hoverinfo="skip"))
    tampil(gaya(f3, "Juta ton CO₂e", 320, 1))
    a, b = ser.loc[2010], ser.loc[T_AKHIR]
    kalimat = f"<b>{pilih}</b>: dari {fmt(a, 1)} juta ton (2010) menjadi {fmt(b, 1)} juta ton ({T_AKHIR}), "
    kalimat += f"{'naik' if b > a else 'turun'} <b>{fmt(abs(b / a - 1) * 100, 0)}%</b>."
    if pilih == "Transportasi":
        kalimat += " Penurunan tajam 2020 bertepatan dengan pembatasan aktivitas masa pandemi."
    sorot(kalimat)

    kotak("Apa bedanya emisi langsung dan tidak langsung?",
          f"Grafik di atas menunjukkan emisi <b>langsung</b> (terjadi di dalam wilayah Jakarta: knalpot, pembangkit, pembakaran bahan bakar, sampah). "
          f"Ada juga emisi <b>tidak langsung</b> dari listrik yang dipakai warga dan gedung Jakarta: <b>{fmt(W.loc[ths, 'Emisi'] / 1000, 1)} juta ton</b> pada {ths}. "
          f"Laporan mencatat keduanya terpisah, tetapi perbandingan dengan baseline memakai jumlah keduanya "
          f"(<b>{fmt(W.loc[ths, 'Grand'] / 1000, 1)} juta ton</b> pada {ths}). Sektor AFOLU (lahan) berupa serapan bersih yang nilainya sangat kecil sehingga tidak ditampilkan.")

# ================================================================== TAB 3
with tab3:
    st.subheader(f"Apa yang Sudah Dilakukan? Capaian Aksi Mitigasi {T_AKHIR}")
    its = AKSI[AKSI["aksi"].str.contains("ITS", case=True)]
    its_v = float(its["reduksi_ton"].iloc[0])
    k1, k2, k3 = st.columns(3)
    k1.metric("Jumlah aksi yang dilaporkan", f"{len(AKSI)} aksi")
    k2.metric("Jumlah penurunan dari seluruh aksi", f"{jt(TOTAL_AKSI)} juta ton")
    k3.metric("Porsi satu aksi terbesar (ITS)", f"{fmt(its_v / TOTAL_AKSI * 100, 0)}%")

    pilih_s = st.radio("Tampilkan sektor", ["Semua"] + list(AKSI["sektor"].unique()), horizontal=True)
    df = AKSI if pilih_s == "Semua" else AKSI[AKSI["sektor"] == pilih_s]
    df = df.sort_values("reduksi_ton")
    fig = go.Figure(go.Bar(
        x=df["reduksi_ton"] / 1e6, y=df["aksi"].str.slice(0, 58), orientation="h", marker_color=[C[x] for x in df["sektor"]],
        text=[f"{fmt(v / 1e6, 2)}" for v in df["reduksi_ton"]], textposition="outside", cliponaxis=False,
        customdata=np.stack([df["reduksi_ton"], df["reduksi_persen_aksi"]], axis=1),
        hovertemplate="%{y}<br>Mengurangi %{customdata[0]:,.0f} ton CO₂e (%{customdata[1]:.1f}% dari emisi sumbernya)<extra></extra>"))
    fig = gaya(fig, None, max(320, 24 * len(df) + 90))
    fig.update_xaxes(title="Penurunan emisi 2025 (juta ton CO₂e)", showgrid=True, gridcolor="#F1F5F9",
                     range=[0, float(df["reduksi_ton"].max()) / 1e6 * 1.2])
    fig.update_layout(margin=dict(l=10, r=40, t=10, b=10))
    tampil(fig)

    st.markdown("**Lihat penjelasan satu aksi**")
    nama = st.selectbox("Pilih aksi", AKSI.sort_values("reduksi_ton", ascending=False)["aksi"].tolist())
    ra = AKSI[AKSI["aksi"] == nama].iloc[0]
    sorot(f"<b>{nama}</b><br>{deskripsi(nama)}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Emisi tanpa aksi", f"{fmt(ra['baseline_ton'] / 1e6, 2)} juta ton")
    m2.metric("Emisi dengan aksi", f"{fmt(ra['mitigasi_ton'] / 1e6, 2)} juta ton")
    m3.metric("Penurunan", f"{fmt(ra['reduksi_ton'] / 1e6, 2)} juta ton")
    m4.metric("Setara % emisi Jakarta", f"{fmt(ra['reduksi_ton'] / c25 * 100, 2)}%")

    kotak("⚠️ Perlu klarifikasi dengan DLH",
          f"<b>1. Dua angka penurunan.</b> Jumlah seluruh aksi = <b>{jt(TOTAL_AKSI)} juta ton</b>, sedangkan penurunan menurut selisih baseline dan "
          f"inventori = <b>{jt(ROW25['reduksi_ton'])} juta ton</b>. Selisih {jt(ROW25['reduksi_ton'] - TOTAL_AKSI)} juta ton tidak dijelaskan oleh aksi yang tercantum.<br>"
          f"<b>2. Baseline ITS.</b> Baseline aksi ITS tercatat {fmt(float(its['baseline_ton'].iloc[0]) / 1e6, 1)} juta ton, lebih besar daripada seluruh "
          f"emisi Jakarta ({jt(c25)} juta ton) dan emisi transportasi ({fmt(SEKTOR.loc[T_AKHIR, 'Transportasi'], 1)} juta ton). "
          "Cara perhitungan baseline per aksi perlu dikonfirmasi.", "kuning")

# ================================================================== TAB 4
with tab4:
    st.subheader("Mau ke Mana? Target Penurunan Emisi Jakarta")
    emisi_target = {2025: float(ROW25["baseline_ton"]) / 1e6 - float(TOT_TARGET[2025]) / 1e3}
    for t in range(2026, 2030):
        emisi_target[t] = BASELINE_GRAFIK[t] - float(TOT_TARGET[t]) / 1e3
    emisi_target[2030] = B2030 / 1e6 - float(TOT_TARGET[2030]) / 1e3
    batas_2030 = emisi_target[2030]

    sorot(f"Target 2030: emisi <b>{fmt(TARGET_PCT, 0)}%</b> di bawah baseline ({jt(B2030)} juta ton), yaitu penurunan "
          f"<b>{fmt(TOT_TARGET[2030] / 1000, 1)} juta ton</b>. Artinya emisi 2030 boleh sampai ± <b>{fmt(batas_2030, 1)} juta ton</b>, "
          f"yang masih <b>{fmt((batas_2030 / (c25 / 1e6) - 1) * 100, 0)}% lebih tinggi</b> daripada emisi {T_AKHIR} ({jt(c25)} juta ton). "
          "Target ini adalah penurunan terhadap baseline yang terus naik, bukan penurunan dari kondisi sekarang.")

    fig = go.Figure()
    h = HIST.loc[T0_CAPAIAN:]
    fig.add_trace(go.Scatter(x=h.index, y=h["inventori_ton"] / 1e6, name="Emisi sebenarnya", mode="lines+markers",
                             line=dict(color=C["inventori"], width=3),
                             hovertemplate="%{x}: %{y:.1f} juta ton<extra></extra>"))
    thb = list(h.index) + [2026, 2027, 2028, 2029, 2030]
    bvals = list(h["baseline_ton"] / 1e6) + [BASELINE_GRAFIK[t] for t in range(2026, 2030)] + [B2030 / 1e6]
    fig.add_trace(go.Scatter(x=thb, y=bvals, name="Baseline (perkiraan tanpa aksi)", mode="lines",
                             line=dict(color=C["baseline"], width=2.5, dash="dash"),
                             hovertemplate="%{x}: baseline %{y:.1f} juta ton<extra></extra>"))
    fig.add_trace(go.Scatter(x=list(emisi_target.keys()), y=list(emisi_target.values()), name="Emisi jika target tercapai",
                             mode="lines+markers", line=dict(color=C["target"], width=3),
                             hovertemplate="%{x}: %{y:.1f} juta ton jika target tercapai<extra></extra>"))
    fig.update_xaxes(range=[T0_CAPAIAN - 0.5, 2030.5])
    tampil(gaya(fig, "Juta ton CO₂e", 400, 1))
    st.caption("Baseline 2026–2029 dibaca dari label Gambar 2 laporan (dibulatkan ke juta ton); 2025 dan 2030 dari tabel. "
               "Garis oranye = baseline dikurangi target penurunan tahunan (Tabel 3).")

    st.markdown(f"**Apakah target {T_AKHIR} tercapai? Tergantung cara menghitungnya**")
    target25 = float(TOT_TARGET[2025]) * 1000
    fig = go.Figure(go.Bar(
        x=["Target penurunan 2025", "Capaian menurut baseline − inventori", "Capaian menurut jumlah aksi"],
        y=[target25 / 1e6, float(ROW25["reduksi_ton"]) / 1e6, TOTAL_AKSI / 1e6],
        marker_color=[C["target"], C["reduksi"], C["abu"]],
        text=[f"{fmt(v / 1e6, 1)}" for v in (target25, float(ROW25["reduksi_ton"]), TOTAL_AKSI)], textposition="outside"))
    fig = gaya(fig, "Juta ton CO₂e", 320)
    fig.update_layout(showlegend=False)
    tampil(fig)
    kotak("Cara membaca",
          f"Menurut selisih baseline dan inventori, capaian {T_AKHIR} (<b>{jt(ROW25['reduksi_ton'])}</b>) melampaui target (<b>{jt(target25)}</b>). "
          f"Menurut jumlah aksi yang tercantum (<b>{jt(TOTAL_AKSI)}</b>), capaian masih di bawah target. "
          "Dua cara hitung ini memberi kesimpulan berbeda, sehingga perlu klarifikasi dengan DLH sebelum disimpulkan.", "kuning")

    st.markdown("**Rincian target per aksi**")
    t1, t2 = st.columns([1, 2])
    with t1:
        tt = st.slider("Pilih tahun target", 2025, 2030, 2030, key="th_target")
    kel = [k for k in TG["kelompok"].unique() if k != "TOTAL"]
    with t2:
        pk = st.selectbox("Pilih kelompok", kel, index=0)
    sub = TG[(TG["kelompok"] == pk) & (TG["level"] == "kelompok") & (TG["tahun"] == tt)]["gg_co2e"].iloc[0]
    sorot(f"Target {tt} untuk <b>{pk}</b>: <b>{fmt(sub / 1000, 2)} juta ton</b> "
          f"({fmt(sub / float(TOT_TARGET[tt]) * 100, 0)}% dari total target {fmt(float(TOT_TARGET[tt]) / 1000, 1)} juta ton).")
    ak = TG[(TG["kelompok"] == pk) & (TG["level"] == "aksi") & (TG["tahun"] == tt) & (TG["gg_co2e"] > 0)].sort_values("gg_co2e")
    if len(ak):
        fig = go.Figure(go.Bar(
            x=ak["gg_co2e"] / 1000, y=ak["aksi"].str.slice(0, 55), orientation="h", marker_color=C["target"],
            text=[fmt(v / 1000, 2) for v in ak["gg_co2e"]], textposition="outside", cliponaxis=False,
            hovertemplate="%{y}: target %{x:.2f} juta ton<extra></extra>"))
        fig = gaya(fig, None, max(260, 26 * len(ak) + 80))
        fig.update_xaxes(title="Target penurunan (juta ton CO₂e)", showgrid=True, gridcolor="#F1F5F9",
                         range=[0, float(ak["gg_co2e"].max()) / 1000 * 1.2])
        fig.update_layout(margin=dict(l=10, r=40, t=10, b=10))
        tampil(fig)
    else:
        st.info("Tidak ada rincian aksi bernilai positif untuk pilihan ini.")

# ================================================================== TAB 5
with tab5:
    st.subheader("Catatan, Keterbatasan, dan Sumber")
    kotak("Hal yang perlu diklarifikasi dengan DLH",
          "<ol>"
          f"<li><b>Dua angka penurunan 2025:</b> {jt(ROW25['reduksi_ton'])} juta ton (baseline − inventori) vs {jt(TOTAL_AKSI)} juta ton (jumlah aksi).</li>"
          "<li><b>Baseline aksi ITS</b> (67,7 juta ton) lebih besar daripada total emisi Jakarta.</li>"
          "<li><b>Target 2030 muncul dalam tiga persentase:</b> 30% (PerGub 90/2021, Tabel 6.1), 32% (pemutakhiran, Bab 6.3 dan Tabel 3), "
          "dan 50% (legenda Gambar 2). Dashboard memakai 32%.</li>"
          "<li><b>Dua tabel target aksi berbeda:</b> Tabel 3 (Ringkasan Eksekutif) dan Tabel 6.3 (Bab VI). Komponen Tabel 3 menjumlah ke total, "
          "komponen Tabel 6.3 tidak, sehingga dashboard memakai Tabel 3.</li>"
          "</ol>", "kuning")
    st.markdown("""
**Cara angka dibentuk**
- **Baseline dan penurunan 2015–2025** direkonstruksi dari Tabel 5.9 (emisi tahunan) dan Tabel 5.17 (% terhadap baseline): baseline = emisi ÷ (1 + persentase). Hasilnya cocok dengan label Gambar 2 laporan.
- **Baseline 2026–2029** dibaca dari label Gambar 2 (dibulatkan); 2030 dari Tabel 6.1.
- **Emisi jika target tercapai** = baseline − target penurunan tahunan (Tabel 3).
- **Penjelasan aksi** ditulis ulang dengan bahasa awam dari nama aksi dan perlu diverifikasi.
- **Intensitas emisi** memakai PDRB harga konstan yang sama dengan laporan; deret PDRB awal (2010–2012) tampak tidak mulus sehingga tren intensitas awal sebaiknya dibaca hati-hati.
""")
    cek = D["cek"].copy()
    cek["status"] = np.where(cek["lolos"], "✅ cocok", "⚠️ berbeda")
    st.markdown(f"**Pemeriksaan konsistensi data** ({int(cek['lolos'].sum())} dari {len(cek)} cocok)")
    tabel(cek[["pemeriksaan", "hasil_hitung", "acuan_laporan", "status", "acuan_sumber"]]
          .rename(columns={"pemeriksaan": "Pemeriksaan", "hasil_hitung": "Hasil hitung", "acuan_laporan": "Acuan laporan",
                           "status": "Status", "acuan_sumber": "Sumber acuan"}))
    st.markdown("**Unduh data**")
    d1, d2, d3 = st.columns(3)
    d1.download_button("📥 Baseline & inventori", BI.to_csv(index=False).encode("utf-8"), "baseline_inventori.csv", "text/csv")
    d2.download_button("📥 Capaian aksi 2025", AKSI.to_csv(index=False).encode("utf-8"), "capaian_aksi_2025.csv", "text/csv")
    d3.download_button("📥 Target 2025–2030", TG.to_csv(index=False).encode("utf-8"), "target_aksi_2025_2030.csv", "text/csv")
