import io
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import engine as eg

# ==========================================================
# KONFIGURASI & GAYA
# ==========================================================
st.set_page_config(
    page_title="LMDI & Simulasi Mitigasi Emisi Rumah Tangga DKI Jakarta",
    page_icon="🌿",
    layout="wide",
)

FONT = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
WARNA = {
    "listrik": "#1E4E79", "bahan_bakar": "#D98A3C", "naik": "#C84B31", "turun": "#1F8A70",
    "total": "#1F2937", "aktual": "#334155", "bau": "#94A3B8", "simulasi": "#0F52BA",
}

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.8rem; padding-bottom: 3rem; max-width: 1220px; }
    .stApp, .stApp p, .stApp li, .stApp label, .stApp td, .stApp th,
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 { font-family: Inter, -apple-system, "Segoe UI", Roboto, sans-serif; }
    .hero-box { background: linear-gradient(135deg, #0F3443 0%, #1E5F74 60%, #2A8C82 100%);
        color: white; padding: 26px 30px; border-radius: 16px;
        box-shadow: 0 10px 25px rgba(15,52,67,.14); margin-bottom: 1.1rem; }
    .hero-badge { display:inline-block; background: rgba(255,255,255,.16); color:#E6FFFA; font-size:.78rem;
        font-weight:600; padding:4px 12px; border-radius:999px; letter-spacing:.03em; text-transform:uppercase; margin-bottom:10px; }
    .hero-title { font-size:1.75rem; font-weight:700; margin:0 0 6px 0; letter-spacing:-.02em; color:#fff; line-height:1.25; }
    .hero-sub { font-size:.96rem; opacity:.9; margin:0; line-height:1.5; max-width:920px; color:#F0FDF4; }
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
    button[data-baseweb="tab"] p { font-weight:600; font-size:.94rem; }
    #MainMenu, footer { visibility:hidden; }
    @media (max-width: 900px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }
    </style>
    """,
    unsafe_allow_html=True,
)


def fmt_id(x, d=0):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_tanda(x, d=0):
    if abs(x) < 0.5 * 10 ** (-d):
        return fmt_id(0, d)
    return ("+" if x > 0 else "−") + fmt_id(abs(x), d)


def kotak(judul, isi_html, warna=""):
    st.markdown(
        f'<div class="kotak {warna}"><div class="kotak-judul">{judul}</div>'
        f'<div style="font-size:0.9rem;color:#334155;">{isi_html}</div></div>',
        unsafe_allow_html=True,
    )


def tata_letak(fig, y_title=None, tinggi=370):
    fig.update_layout(
        template="plotly_white", font=dict(family=FONT, size=12, color="#1E293B"),
        paper_bgcolor="white", plot_bgcolor="white", margin=dict(l=10, r=10, t=36, b=10), height=tinggi,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title_text=""),
        hovermode="x unified", yaxis=dict(title=y_title, gridcolor="#F1F5F9", zerolinecolor="#CBD5E1"),
        xaxis=dict(showgrid=False),
    )
    return fig


def tampil(fig):
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ==========================================================
# DATA (dari CSV — satu sumber kebenaran, ada kolom Status & Catatan)
# ==========================================================
@st.cache_data
def muat_data():
    return pd.read_csv(Path(__file__).parent / "data_rt_dki.csv")


D = muat_data()
F = eg.bangun_frame(D)
T0, T1 = int(F["Tahun"].min()), int(F["Tahun"].max())
T_PROY = 2030
NAMA = eg.NAMA_EFEK


def baris_ke_tabel(rows, kolom_awal="Periode", per_tahun=False):
    out = pd.DataFrame({kolom_awal: [r["Periode"] for r in rows]})
    out["Total perubahan"] = [fmt_tanda(r["total"] / (r.get("n", 1) if per_tahun else 1), 1) for r in rows]
    for k in eg.EFEK:
        out[NAMA[k]] = [fmt_tanda(r[k] / (r.get("n", 1) if per_tahun else 1), 1) for r in rows]
    return out


def ringkas_efek(h):
    items = [(NAMA[k], h[k]) for k in eg.EFEK]
    naik = sorted([x for x in items if x[1] > 0.5], key=lambda x: -x[1])
    turun = sorted([x for x in items if x[1] < -0.5], key=lambda x: x[1])
    a = ", ".join(f"<b>{n}</b> ({fmt_tanda(v)} Gg)" for n, v in naik) or "tidak ada"
    b = ", ".join(f"<b>{n}</b> ({fmt_tanda(v)} Gg)" for n, v in turun) or "tidak ada"
    return a, b


def buat_waterfall(h, tinggi=380):
    nilai = [h[k] for k in eg.EFEK] + [h["total"]]
    label = [NAMA[k].replace(" (", "<br>(") for k in eg.EFEK] + ["Total<br>perubahan"]
    fig = go.Figure(go.Waterfall(
        orientation="v", measure=["relative"] * 5 + ["total"], x=label, y=nilai,
        text=[fmt_tanda(v) for v in nilai], textposition="outside", cliponaxis=False,
        connector={"line": {"color": "#CBD5E1", "width": 1}},
        increasing={"marker": {"color": WARNA["naik"]}}, decreasing={"marker": {"color": WARNA["turun"]}},
        totals={"marker": {"color": WARNA["total"]}}, hovertemplate="%{y:,.1f} Gg CO₂e<extra></extra>",
    ))
    fig = tata_letak(fig, "Gg CO₂e", tinggi)
    fig.update_layout(hovermode="closest")
    return fig


# ==========================================================
# SIDEBAR
# ==========================================================
with st.sidebar:
    st.markdown("### 🎓 Identitas Penelitian")
    st.caption(
        "**Dekomposisi Pendorong Perubahan Emisi GRK Sektor Rumah Tangga DKI Jakarta (2010–2025) "
        "dan Simulasi Mitigasi Berbasis Faktor LMDI (2025–2030)**"
    )
    st.caption(
        "**Peneliti:** Dewantara Putra Makmur  \n**NIM:** G2401231071  \n"
        "**Pembimbing 1:** Perdinan, S.Si., M.Nat.Res.Econ., Ph.D.  \n"
        "**Program Studi:** Meteorologi Terapan, GFM FMIPA IPB"
    )
    st.divider()
    st.markdown("### 🔗 Satu Kerangka Metode")
    st.latex(r"C=\sum_{i} P\cdot\frac{Y}{P}\cdot\frac{E}{Y}\cdot\frac{E_i}{E}\cdot\frac{C_i}{E_i}")
    st.caption(
        "i = listrik, bahan bakar gas (LPG + gas bumi). LMDI-I aditif (Ang 2005, 2015) dipakai untuk "
        "**mendiagnosis** 2010–2025; identitas yang sama dipakai untuk **memproyeksikan** 2025–2030, "
        "lalu diuji dengan **backtest**."
    )
    st.divider()
    st.caption("Sumber data: Laporan Akhir Inventarisasi & Penurunan Emisi GRK DKI Jakarta (DLH 2026). "
               "Status tiap angka ada di tab 4.1.")

# ==========================================================
# HERO & KPI
# ==========================================================
r10, r_prev, r_last = F.loc[T0], F.loc[T1 - 1], F.loc[T1]
c10, c_prev, c_last = r10["C_T"], r_prev["C_T"], r_last["C_T"]
porsi_l = r_last["C_L"] / c_last
kap10, kap_last = c10 / r10["P"] / 1000, c_last / r_last["P"] / 1000
tgt_a, tgt_b = list(eg.TARGET_LABEL.values())

st.markdown(
    """
    <div class="hero-box">
        <div class="hero-badge">Dekomposisi LMDI · Proyeksi Berbasis Faktor · Backtest</div>
        <div class="hero-title">Emisi Gas Rumah Kaca Sektor Rumah Tangga DKI Jakarta</div>
        <div class="hero-sub">Menguraikan pendorong emisi 2010–2025 dengan LMDI-I aditif, menguji kekokohannya,
        lalu memproyeksikan 2025–2030 dengan identitas yang sama dan mengukur seberapa andal proyeksi itu lewat backtest.</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    f"""
    <div class="kpi-grid">
      <div class="kpi-card warn"><div class="kpi-label">Total Emisi Rumah Tangga ({T1})</div>
        <div class="kpi-val">{fmt_id(c_last)} Gg CO₂e</div>
        <div class="kpi-delta">{fmt_tanda((c_last / c10 - 1) * 100, 1)}% vs {T0} · {fmt_tanda((c_last / c_prev - 1) * 100, 1)}% vs {T1 - 1}</div></div>
      <div class="kpi-card gold"><div class="kpi-label">Emisi per Penduduk ({T1})</div>
        <div class="kpi-val">{fmt_id(kap_last, 2)} tCO₂e/jiwa</div>
        <div class="kpi-delta">{fmt_tanda((kap_last / kap10 - 1) * 100, 1)}% vs {T0}</div></div>
      <div class="kpi-card"><div class="kpi-label">Porsi Emisi Listrik ({T1})</div>
        <div class="kpi-val">{fmt_id(porsi_l * 100, 1)}%</div>
        <div class="kpi-delta">{fmt_id(r_last['C_L'])} Gg (emisi tidak langsung)</div></div>
      <div class="kpi-card good"><div class="kpi-label">Target Reduksi Efisiensi RT 2030 (DLH)</div>
        <div class="kpi-val">{fmt_id(tgt_b[2030])}–{fmt_id(tgt_a[2030])} Gg</div>
        <div class="kpi-delta">dua tabel laporan berbeda angka · {fmt_id(tgt_b[2030] / c_last * 100, 0)}–{fmt_id(tgt_a[2030] / c_last * 100, 0)}% emisi {T1}</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏠 Ringkasan Alur", "📊 4.1 Data & Provenansi", "🔍 4.2 Faktor Pendorong (LMDI)",
    "⚖️ 4.3 Uji Kekokohan", "🎛️ 4.4 Proyeksi, Backtest & Simulasi", "📌 Asumsi & Keterbatasan",
])

# ==========================================================
# TAB 0
# ==========================================================
with tab0:
    h_all = eg.lmdi_periode(F, T0, T1, "rantai")
    naik_txt, turun_txt = ringkas_efek(h_all)
    kotak(
        "Alur Penelitian",
        "<ul>"
        f"<li><b>Data (4.1):</b> emisi naik {fmt_tanda((c_last / c10 - 1) * 100, 1)}% sejak {T0} menjadi {fmt_id(c_last)} Gg CO₂e; "
        f"{fmt_id(porsi_l * 100, 1)}% dari listrik. Setiap angka diberi status sumber.</li>"
        f"<li><b>Diagnosis (4.2):</b> pada {T0}–{T1} pendorong kenaikan: {naik_txt}. Penahan: {turun_txt}.</li>"
        "<li><b>Kekokohan (4.3):</b> hasil diuji terhadap metode (rantai vs dua titik), pilihan faktor emisi, "
        "periode pandemi, dan derau pembulatan data.</li>"
        "<li><b>Proyeksi (4.4):</b> setiap faktor identitas diproyeksikan dari tren historis, tuas kebijakan "
        "(labelling, dekarbonisasi grid, pergeseran LPG→listrik) diterapkan, dan <b>keandalan proyeksi diukur lewat backtest</b>.</li>"
        "</ul>",
        "hijau",
    )
    with st.expander("📖 Kamus faktor"):
        st.markdown(
            """
| Simbol | Faktor | Dalam diagnosis (2010–2025) | Dalam proyeksi (2025–2030) |
|---|---|---|---|
| $P$ | Penduduk | Efek pertumbuhan penduduk | Tumbuh sesuai tren periode acuan |
| $Y/P$ | Kemakmuran (PDRB konstan per kapita) | Efek kemakmuran | Tumbuh sesuai tren periode acuan |
| $E/Y$ | Intensitas energi | Efek intensitas (mencakup efisiensi **dan** perubahan struktur) | Tren acuan + **tuas labelling** |
| $E_i/E$ | Bauran energi | Efek bauran listrik vs bahan bakar gas | Tren acuan + **tuas pergeseran LPG→listrik** |
| $C_i/E_i$ | Faktor emisi | Efek faktor emisi | **Tuas dekarbonisasi grid** |
"""
        )

# ==========================================================
# TAB 1 — DATA
# ==========================================================
with tab1:
    st.subheader(f"4.1 Profil Emisi dan Energi Rumah Tangga ({T0}–{T1}) dan Provenansi Data")
    kotak(
        "Cara data dibangun",
        "Emisi listrik, LPG, dan gas bumi dari laporan DLH. Konsumsi energi (TJ): untuk listrik memakai <b>GWh yang dilaporkan</b> bila tersedia "
        f"(saat ini hanya {T1}); selebihnya diturunkan dari <i>E = C / EF</i>. Karena itu efek intensitas pada tahun-tahun turunan belum "
        "sepenuhnya independen dari emisi — mengisi kolom <code>GWh_RT_Lapor</code> di CSV (statistik PLN) akan memperbaikinya otomatis. "
        "LPG dan gas bumi digabung menjadi satu pembawa <i>bahan bakar gas</i> (gas bumi &lt;0,05% emisi; menghindari nilai nol).",
        "kuning",
    )
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Emisi per pembawa energi (Gg CO₂e)**")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=F["Tahun"], y=F["C_L"], name="Listrik (tidak langsung)", marker_color=WARNA["listrik"]))
        fig.add_trace(go.Bar(x=F["Tahun"], y=F["C_B"], name="LPG + gas bumi (langsung)", marker_color=WARNA["bahan_bakar"]))
        fig.update_layout(barmode="stack")
        tampil(tata_letak(fig, "Gg CO₂e"))
    with c2:
        st.markdown("**Konsumsi energi final (TJ)**")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=F["Tahun"], y=F["E_L"], name="Listrik", mode="lines", stackgroup="e",
                                 line=dict(width=1.2, color=WARNA["listrik"])))
        fig.add_trace(go.Scatter(x=F["Tahun"], y=F["E_B"], name="LPG + gas bumi", mode="lines", stackgroup="e",
                                 line=dict(width=1.2, color=WARNA["bahan_bakar"])))
        tampil(tata_letak(fig, "TJ"))

    st.markdown("**Temuan konsistensi data yang perlu diverifikasi sebelum sidang**")
    st.markdown(
        """
1. **Label tahun PDRB/penduduk di laporan 2026 tidak konsisten:** Bab 2.2 menyebut PDRB berlaku 3.926 T untuk "2026", grafik (Gambar 2.3) melabelinya 2025, sedangkan Bab 2.3 menyebut PDRB 2025 = 3.679 T (padahal grafik: 3.679 = 2024). Aplikasi mengikuti **grafik**.
2. **PDRB konstan 2025 adalah turunan** (2024 × (1 + 5,12%)); laporan 2026 tidak memuat deret PDRB konstan. Cek ke BPS (ADHK 2010).
3. **PDRB konstan 2010–2012 janggal:** naik 16,7% pada 2011 lalu turun 3,0% pada 2012, dan konstan > berlaku pada 2011. Tahun 2010 adalah titik awal seluruh dekomposisi, jadi ini penting.
4. **Catatan Tabel 3.6 (EF listrik) bertentangan dengan isinya:** catatan bilang EF 2020–2025 "diasumsikan sama dengan 2019", tetapi nilainya bervariasi (0,902; 0,896; 0,901; 0,903; 0,906) dan 2025 = 2024. Artinya efek faktor emisi pasca-2019 sebagian besar merupakan konvensi data, bukan hasil pengukuran.
5. **EF efektif 2025 = emisi/GWh = 0,9034 tCO₂/MWh**, sedikit di bawah EF tabel (0,906).
6. **Dua tabel target berbeda untuk rumah tangga:** Tabel 3 (Labelling, 2.442→3.630 Gg) vs Tabel 6.5 (Efisiensi Energi RT, 893→3.322 Gg). Aplikasi menyediakan keduanya.
7. **Emisi langsung dilaporkan CO₂e** (CH₄/N₂O Tier 1 ikut), sedangkan konversi ke TJ memakai EF CO₂ saja → energi LPG sedikit terlalu besar (orde <1%).
8. **Emisi listrik 2020 dan 2021 identik (13.100):** kemungkinan hasil pembulatan/estimasi.
"""
    )
    with st.expander("📋 Tabel data lengkap + status/catatan per tahun"):
        tbl = D.copy()
        st.dataframe(tbl, hide_index=True, use_container_width=True)
        st.download_button("📥 Unduh CSV", tbl.to_csv(index=False).encode("utf-8"), "data_rt_dki.csv", "text/csv")

# ==========================================================
# TAB 2 — LMDI
# ==========================================================
with tab2:
    st.subheader(f"4.2 Dekomposisi Faktor Pendorong Emisi ({T0}–{T1})")
    kotak(
        "Cara membaca",
        "Batang <b style='color:#C84B31'>merah</b> mendorong kenaikan, <b style='color:#1F8A70'>hijau</b> menahan. "
        "Jumlah lima efek selalu sama dengan perubahan total (LMDI-I aditif tidak memiliki residual secara konstruksi — "
        "ini sifat metode, <b>bukan</b> bukti validitas; validitas diuji di 4.3 dan 4.4). "
        "Efek &lsquo;intensitas energi&rsquo; mencakup efisiensi dan perubahan struktur ekonomi sehingga tidak identik dengan efisiensi alat.",
    )
    o1, o2, o3 = st.columns(3)
    with o1:
        t_awal = st.selectbox("Tahun awal", list(range(T0, T1)), index=0)
    with o2:
        opsi = list(range(t_awal + 1, T1 + 1))
        t_akhir = st.selectbox("Tahun akhir", opsi, index=len(opsi) - 1)
    with o3:
        metode = st.radio("Metode", ["Rantai tahunan", "Dua titik"], horizontal=True)
    m_key = "rantai" if metode == "Rantai tahunan" else "dua titik"
    hp = eg.lmdi_periode(F, t_awal, t_akhir, m_key)
    st.markdown(f"**Waterfall dekomposisi {t_awal}–{t_akhir} ({metode.lower()}, Gg CO₂e)**")
    tampil(buat_waterfall(hp))
    a_txt, b_txt = ringkas_efek(hp)
    kotak("Ringkasan periode terpilih",
          f"Emisi berubah <b>{fmt_tanda(hp['total'])} Gg CO₂e</b>. Pendorong kenaikan: {a_txt}. Penahan: {b_txt}.")

    fase = [(T0, 2019, "Pra-pandemi"), (2019, 2021, "Pandemi & pemulihan awal"),
            (2021, T1, "Pasca-pandemi"), (T0, T1, "Total")]
    rows = []
    for a, b, nm in fase:
        r = eg.lmdi_periode(F, a, b, "rantai")
        r.update(Periode=f"{nm} ({a}–{b})", n=b - a)
        rows.append(r)
    st.markdown("**Tiga fase (rantai tahunan) — total (Gg) dan per tahun (Gg/tahun, agar fase berbeda panjang sebanding)**")
    tc1, tc2 = st.columns(2)
    with tc1:
        st.dataframe(baris_ke_tabel(rows, "Fase"), hide_index=True, use_container_width=True)
    with tc2:
        st.dataframe(baris_ke_tabel(rows, "Fase", per_tahun=True), hide_index=True, use_container_width=True)

    with st.expander("📈 Dekomposisi tahunan berantai"):
        rantai = pd.DataFrame([eg.lmdi_baris(F.loc[y], F.loc[y + 1]) for y in range(T0, T1)])
        rantai["Periode"] = [f"{y}–{y + 1}" for y in range(T0, T1)]
        wr = {"pop": "#E9B872", "aff": WARNA["naik"], "int": WARNA["turun"], "mix": "#8E7CC3", "ef": "#4FB3D9"}
        fig_c = go.Figure()
        for k in eg.EFEK:
            fig_c.add_trace(go.Bar(name=NAMA[k], x=rantai["Periode"], y=rantai[k], marker_color=wr[k]))
        fig_c.add_trace(go.Scatter(name="Total perubahan", x=rantai["Periode"], y=rantai["total"],
                                   mode="lines+markers", line=dict(color="#0F172A", width=2.5)))
        fig_c.update_layout(barmode="relative")
        tampil(tata_letak(fig_c, "Gg CO₂e", 360))
        st.caption("Perubahan tahunan kecil (±100 Gg) sebanding dengan pembulatan data sumber; baca tren multi-tahun, bukan satu tahun.")
        st.download_button("📥 Unduh dekomposisi multi-fase (CSV)", pd.DataFrame(rows).to_csv(index=False).encode("utf-8"),
                           "dekomposisi_lmdi.csv", "text/csv")

# ==========================================================
# TAB 3 — UJI KEKOKOHAN
# ==========================================================
with tab3:
    st.subheader("4.3 Uji Kekokohan Hasil Dekomposisi")
    kotak(
        "Apa yang diuji",
        "Bukan sekadar mengganti data yang jelas keliru (mis. PDRB berlaku), tetapi pilihan-pilihan analis yang sah: "
        "<b>(1)</b> metode rantai vs dua titik, <b>(2)</b> pilihan faktor emisi, <b>(3)</b> perlakuan periode pandemi tanpa "
        "membuang tahun, <b>(4)</b> derau pembulatan data sumber, <b>(5)</b> variabel aktivitas alternatif bila datanya tersedia.",
    )
    ua, ub = T0, T1

    @st.cache_data
    def varian(a, b):
        v = {}
        v["Baseline: rantai tahunan"] = eg.lmdi_periode(F, a, b, "rantai")
        v["Dua titik (satu langkah)"] = eg.lmdi_periode(F, a, b, "dua titik")
        ef19 = float(D.loc[D["Tahun"] == 2019, "EF_Listrik_tCO2_MWh"].iloc[0])
        ef_beku = np.where(D["Tahun"] >= 2019, ef19, D["EF_Listrik_tCO2_MWh"])
        v["EF listrik dibekukan di nilai 2019"] = eg.lmdi_periode(eg.bangun_frame(D, ef_listrik=ef_beku), a, b, "rantai")
        v["EF LPG/gas Tier 1 IPCC"] = eg.lmdi_periode(
            eg.bangun_frame(D, ef_lpg=eg.EF_LPG_T1, ef_gas=eg.EF_GAS_T1), a, b, "rantai")
        return v

    @st.cache_data
    def derau(a, b):
        return eg.mc_pembulatan(D, a, b, n=200, rel=0.005)

    V = varian(ua, ub)
    st.markdown(f"**Uji 1–2: metode dan faktor emisi ({ua}–{ub}, Gg CO₂e)**")
    palet = ["#1E4E79", "#D98A3C", "#4E9A84", "#8E7CC3"]
    fig_v = go.Figure()
    for (nm, h), w in zip(V.items(), palet):
        fig_v.add_trace(go.Bar(name=nm, x=[NAMA[k] for k in eg.EFEK], y=[h[k] for k in eg.EFEK], marker_color=w))
    fig_v.update_layout(barmode="group")
    tampil(tata_letak(fig_v, "Gg CO₂e", 360))
    rows_v = []
    for nm, h in V.items():
        r = dict(h)
        r["Periode"] = nm
        rows_v.append(r)
    st.dataframe(baris_ke_tabel(rows_v, "Varian"), hide_index=True, use_container_width=True)

    # kesimpulan dinamis
    tanda_sama, urut_sama = True, True
    base = V["Baseline: rantai tahunan"]
    urut_base = sorted(eg.EFEK, key=lambda k: -abs(base[k]))[:2]
    beda = []
    for nm, h in V.items():
        for k in eg.EFEK:
            if np.sign(h[k]) != np.sign(base[k]) and abs(base[k]) > 1:
                tanda_sama = False
                beda.append(f"{NAMA[k]} ({nm})")
        if sorted(eg.EFEK, key=lambda k: -abs(h[k]))[:2] != urut_base:
            urut_sama = False
    rentang_aff = [h["aff"] for h in V.values()]
    rentang_ef = [h["ef"] for h in V.values()]
    kal = (f"Tanda kelima efek {'sama' if tanda_sama else 'BERBEDA pada: ' + ', '.join(beda)} di semua varian; "
           f"dua efek terbesar ({', '.join(NAMA[k] for k in urut_base)}) "
           f"{'tetap sama' if urut_sama else 'berubah pada sebagian varian'}. "
           f"Besaran efek kemakmuran berkisar {fmt_id(min(rentang_aff))}–{fmt_id(max(rentang_aff))} Gg; "
           f"efek faktor emisi {fmt_id(min(rentang_ef))}–{fmt_id(max(rentang_ef))} Gg "
           "(paling bergantung pada metode, karena faktor emisi berubah tajam pada 2010–2016).")
    kotak("Kesimpulan Uji 1–2", kal, "hijau")

    st.markdown("**Uji 3: pandemi — efek per tahun pada tiap fase (tanpa membuang tahun mana pun)**")
    rows_f = []
    for a, b, nm in fase[:3]:
        r = eg.lmdi_periode(F, a, b, "rantai")
        r.update(Periode=f"{nm} ({a}–{b})", n=b - a)
        rows_f.append(r)
    st.dataframe(baris_ke_tabel(rows_f, "Fase", per_tahun=True), hide_index=True, use_container_width=True)
    hf = rows_f[1]
    kotak(
        "Cara membaca Uji 3",
        f"Pada fase pandemi, efek intensitas energi = <b>{fmt_tanda(hf['int'] / hf['n'], 1)} Gg/tahun</b> "
        f"(fase pra-pandemi: {fmt_tanda(rows_f[0]['int'] / rows_f[0]['n'], 1)}; pasca: {fmt_tanda(rows_f[2]['int'] / rows_f[2]['n'], 1)}). "
        "Pola ini <i>konsisten dengan</i> hipotesis kerja-dari-rumah (listrik hunian naik saat PDRB turun), tetapi LMDI tidak dapat "
        "membuktikan perilaku; pengujiannya butuh data tambahan (mis. data jam-beban, suhu, mobilitas).",
    )

    st.markdown("**Uji 4: derau pembulatan data sumber (±0,5% acak pada emisi listrik dan LPG, 200 simulasi, rantai tahunan)**")
    mc = derau(ua, ub)
    q = mc[eg.EFEK + ["total"]].quantile([0.05, 0.5, 0.95]).T
    q.index = [NAMA.get(i, "Total perubahan") for i in q.index]
    q = q.rename(columns={0.05: "P5", 0.5: "Median", 0.95: "P95"})
    q = q.apply(lambda kol: kol.map(lambda v: fmt_tanda(v, 0)))
    st.dataframe(q.reset_index().rename(columns={"index": "Efek"}), hide_index=True, use_container_width=True)
    lebar = {k: (mc[k].quantile(0.95) - mc[k].quantile(0.05)) / max(abs(mc[k].median()), 1e-9) * 100 for k in eg.EFEK}
    k_maks = max(lebar, key=lebar.get)
    st.caption(f"Lebar rentang P5–P95 terbesar (relatif): {NAMA[k_maks]} ≈ {fmt_id(lebar[k_maks], 0)}% dari mediannya. "
               "Rentang kecil berarti kesimpulan tidak rapuh terhadap pembulatan; ini bukan jaminan data sumber benar.")

    st.markdown("**Uji 5: variabel aktivitas alternatif**")
    if "PKRT_Konstan_T" in D.columns and D["PKRT_Konstan_T"].notna().all():
        Fk = F.copy()
        Fk["PKRT_Konstan_T"] = D["PKRT_Konstan_T"].to_numpy()
        h_alt = eg.lmdi_periode(Fk, ua, ub, "rantai", aktivitas="PKRT_Konstan_T")
        st.dataframe(baris_ke_tabel([dict(V["Baseline: rantai tahunan"], Periode="PDRB konstan"),
                                     dict(h_alt, Periode="Pengeluaran konsumsi RT konstan")], "Aktivitas"),
                     hide_index=True, use_container_width=True)
    else:
        st.info("Kolom `PKRT_Konstan_T` (pengeluaran konsumsi rumah tangga, BPS) belum diisi di data_rt_dki.csv. "
                "Mengisinya mengaktifkan uji ini secara otomatis — direkomendasikan karena PDRB total mencakup aktivitas non-rumah-tangga.")

# ==========================================================
# TAB 4 — PROYEKSI, BACKTEST, SIMULASI
# ==========================================================
with tab4:
    st.subheader(f"4.4 Proyeksi {T1}–{T_PROY}: Backtest dan Simulasi Mitigasi")
    kotak(
        "Cara kerja",
        f"Tahun dasar = <b>{T1}</b> (data aktual terbaru, bukan proyeksi). Setiap faktor identitas (P, Y/P, E/Y, bauran, EF) "
        "tumbuh mengikuti tren periode acuan; baseline = tren tanpa program baru. Tuas kebijakan lalu diterapkan pada energi/EF, "
        "dan dekomposisi LMDI menghitung ulang kontribusi tiap faktor. <b>Keandalan tren diukur dulu lewat backtest</b>.",
    )

    # ---- 1. Periode acuan & backtest ----
    st.markdown("**1. Periode acuan tren & validasi (backtest)**")
    mulai = st.radio("Tren dihitung dari tahun:", [2015, 2019, 2020, 2021], index=1, horizontal=True,
                     help="2019 mencakup satu siklus penuh (pra-pandemi → pemulihan). 2020 memakai tahun pandemi sebagai dasar sehingga tren kemakmuran terlalu tinggi.")
    par = eg.tren(F, mulai, T1)
    det, ring = eg.backtest(F, w=5)

    tabel_bt = pd.DataFrame({
        "Horizon (tahun)": ring["h"], "n uji": ring["n"],
        "Bias proyeksi tren (%)": ring["bias_mesin"].map(lambda v: fmt_tanda(v, 1)),
        "RMSE proyeksi tren (%)": ring["rmse_mesin"].map(lambda v: fmt_id(v, 1)),
        "RMSE 'tanpa perubahan' (%)": ring["rmse_persisten"].map(lambda v: fmt_id(v, 1)),
        "RMSE ekstrapolasi CAGR emisi (%)": ring["rmse_naif_cagr"].map(lambda v: fmt_id(v, 1)),
    })
    bt1, bt2 = st.columns([3, 2])
    with bt1:
        st.dataframe(tabel_bt, hide_index=True, use_container_width=True)
    with bt2:
        fig_bt = go.Figure()
        fig_bt.add_trace(go.Scatter(x=ring["h"], y=ring["rmse_mesin"], name="Proyeksi tren", mode="lines+markers",
                                    line=dict(color=WARNA["simulasi"], width=3)))
        fig_bt.add_trace(go.Scatter(x=ring["h"], y=ring["rmse_persisten"], name="Tanpa perubahan", mode="lines+markers",
                                    line=dict(color=WARNA["bau"], width=2, dash="dash")))
        fig_bt.update_xaxes(dtick=1, title="Horizon (tahun)")
        tampil(tata_letak(fig_bt, "RMSE (%)", 250))
    hmax = int(ring["h"].max())
    rm = float(ring.loc[ring["h"] == hmax, "rmse_mesin"].iloc[0])
    rp = float(ring.loc[ring["h"] == hmax, "rmse_persisten"].iloc[0])
    h1m = float(ring.loc[ring["h"] == 1, "rmse_mesin"].iloc[0])
    h1p = float(ring.loc[ring["h"] == 1, "rmse_persisten"].iloc[0])
    tgt_pct = tgt_a[T_PROY] / c_last * 100
    kotak(
        "Hasil backtest (rolling-origin, jendela tren 5 tahun)",
        f"Galat RMSE proyeksi tren: <b>{fmt_id(h1m, 1)}%</b> pada horizon 1 tahun dan <b>{fmt_id(rm, 1)}%</b> pada horizon {hmax} tahun. "
        f"Pembanding &lsquo;tanpa perubahan&rsquo;: {fmt_id(h1p, 1)}% dan {fmt_id(rp, 1)}%. "
        + ("Proyeksi tren <b>tidak lebih akurat</b> daripada asumsi tanpa perubahan pada horizon-horizon ini — wajar karena deret hanya 16 tahun dan "
           "memuat guncangan pandemi serta lompatan faktor emisi 2010–2016. " if rm >= rp else
           "Proyeksi tren lebih akurat daripada asumsi tanpa perubahan pada horizon terjauh. ")
        + f"Sebagai perbandingan, target labelling 2030 setara ±{fmt_id(tgt_pct, 0)}% emisi {T1}: efek kebijakan berada pada orde yang sama dengan "
        "galat proyeksi baseline, sehingga hasil simulasi harus dibaca sebagai <b>rentang</b>, bukan angka tunggal.",
        "kuning",
    )

    # ---- 2. Skenario ----
    st.markdown("**2. Skenario kebijakan**")
    sumber_t = st.radio("Sumber target reduksi efisiensi energi rumah tangga:", list(eg.TARGET_LABEL.keys()), index=0,
                        help="Laporan DLH 2026 memuat dua tabel berbeda untuk aksi ini; pilih dan bandingkan.")
    target = eg.TARGET_LABEL[sumber_t]
    selisih_cal, real_cal = eg.kalibrasi_realisasi(F, target[T1], w=(T1 - 1) - mulai)

    kotak(
        f"Kalibrasi dengan data aktual {T1}",
        f"Ramalan baseline untuk {T1} (tren hingga {T1 - 1}) melebihi emisi aktual sebesar <b>{fmt_id(selisih_cal)} Gg</b>, sedangkan target "
        f"program {T1} menurut tabel terpilih = {fmt_id(target[T1])} Gg. Maka realisasi program <b>paling tinggi ≈ {fmt_id(real_cal * 100, 0)}%</b> "
        "dari target (batas atas, karena selisih itu juga memuat cuaca, perilaku, dan galat tren). Di Tabel capaian mitigasi 2025 laporan, "
        "program ini tidak muncul sebagai capaian terlapor. Preset &lsquo;Realisasi terkalibrasi&rsquo; memakai angka ini.",
    )

    preset = st.radio(
        "Preset", ["Tanpa program (BAU)", "Realisasi terkalibrasi", "Target DLH penuh",
                   "Target DLH + grid lebih bersih", "Atur sendiri"], index=1, horizontal=True,
        label_visibility="collapsed")
    peta = {
        "Tanpa program (BAU)": (0, 0, 0),
        "Realisasi terkalibrasi": (int(round(real_cal * 100)), 0, 0),
        "Target DLH penuh": (100, 0, 0),
        "Target DLH + grid lebih bersih": (100, 10, 0),
    }
    d_real, d_grid, d_shift = peta.get(preset, (50, 0, 0))
    kunci = preset != "Atur sendiri"
    s1, s2, s3 = st.columns(3)
    with s1:
        real = st.slider("Realisasi program efisiensi (% dari target tabel)", 0, 100, d_real, 5, disabled=kunci,
                         key=f"real_{preset}_{sumber_t[:7]}_{mulai}",
                         help="Mengurangi kebutuhan listrik sebesar target (Gg) ÷ EF listrik tahun dasar → menekan E/Y.")
    with s2:
        grid = st.slider("Penurunan EF listrik pada 2030 (%)", 0, 40, d_grid, 5, disabled=kunci,
                         key=f"grid_{preset}_{mulai}",
                         help="ASUMSI skenario — laporan DLH tidak memuat target EF grid. Sebaiknya ditautkan ke RUPTL/JETP.")
    with s3:
        shift = st.slider("Pergeseran LPG→listrik (% energi LPG pada 2030)", 0, 30, d_shift, 5, disabled=kunci,
                          key=f"shift_{preset}_{mulai}",
                          help="Mis. kompor induksi. Tuas bauran energi (faktor ke-4 LMDI).")
    with st.expander("⚙️ Asumsi lanjutan (tren & efisiensi relatif listrik vs LPG)"):
        eta = st.slider("Energi listrik per energi LPG pada pemakaian akhir (η, ASUMSI)", 0.40, 1.00, 0.65, 0.05,
                        help="<1 berarti listrik lebih efisien pada pemakaian akhir. Perlu rujukan literatur.")
        manual = st.checkbox("Ubah asumsi tren manual")
        par_u = dict(par)
        if manual:
            m1, m2, m3, m4 = st.columns(4)
            par_u["r_P"] = m1.slider("Laju penduduk (%/th)", -0.5, 2.0, float(round(par["r_P"] * 100, 2)), 0.05,
                                      key=f"rp_{mulai}") / 100
            par_u["r_g"] = m2.slider("Laju PDRB/kapita (%/th)", 0.0, 8.0, float(round(par["r_g"] * 100, 2)), 0.1,
                                      key=f"rg_{mulai}") / 100
            par_u["r_I"] = m3.slider("Laju E/Y (%/th)", -5.0, 2.0, float(round(par["r_I"] * 100, 2)), 0.1,
                                      key=f"ri_{mulai}") / 100
            par_u["d_sL"] = m4.slider("Δ porsi listrik (poin/th)", -0.5, 1.0, float(round(par["d_sL"] * 100, 2)), 0.05,
                                       key=f"ds_{mulai}") / 100
        else:
            st.caption(
                f"Tren {mulai}–{T1}: penduduk {fmt_tanda(par['r_P'] * 100, 2)}%/th · PDRB/kapita {fmt_tanda(par['r_g'] * 100, 2)}%/th · "
                f"E/Y {fmt_tanda(par['r_I'] * 100, 2)}%/th · porsi listrik {fmt_tanda(par['d_sL'] * 100, 2)} poin/th.")

    hasil = eg.proyeksi(F.loc[T1], par_u, T_PROY, target, real / 100, grid / 100, shift / 100, eta)
    dfp = hasil["df"]
    c_bau30, c_sim30 = float(dfp["BAU"].iloc[-1]), float(dfp["Skenario"].iloc[-1])
    red30 = c_bau30 - c_sim30
    if hasil["cap_kena"]:
        st.warning("Reduksi labelling melebihi 70% listrik baseline pada sebagian tahun, sehingga dibatasi. Turunkan realisasi.")

    st.markdown(f"**3. Hasil simulasi {T_PROY}**")
    ring_i = ring.set_index("h")
    n_h = len(dfp) - 1
    rm_t = float(ring_i["rmse_mesin"].loc[min(n_h, hmax)])
    m1, m2, m3 = st.columns(3)
    m1.metric(f"Emisi RT {T_PROY} (skenario)", f"{fmt_id(c_sim30)} Gg CO₂e",
              f"{fmt_tanda(c_sim30 - c_last)} Gg vs aktual {T1}", delta_color="inverse")
    m2.metric(f"Selisih terhadap baseline {T_PROY}", f"{fmt_tanda(-red30)} Gg",
              f"baseline {fmt_id(c_bau30)} Gg ({fmt_tanda((c_bau30 / c_last - 1) * 100, 1)}% vs {T1})", delta_color="off")
    m3.metric("Rentang galat proyeksi (backtest)", f"±{fmt_id(rm_t, 0)}% ≈ ±{fmt_id(c_sim30 * rm_t / 100)} Gg",
              f"RMSE horizon {min(n_h, hmax)} th", delta_color="off")

    g1, g2 = st.columns(2)
    with g1:
        st.markdown(f"**Lintasan aktual ({T1 - 10}–{T1}) dan proyeksi ({T1}–{T_PROY})**")
        hist = F[F["Tahun"] >= T1 - 10]
        pita = np.array([0.0] + [float(ring_i["rmse_mesin"].loc[min(k, hmax)]) for k in range(1, n_h + 1)]) / 100
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist["Tahun"], y=hist["C_T"], name="Aktual", mode="lines+markers",
                                 line=dict(color=WARNA["aktual"], width=2.5)))
        fig.add_trace(go.Scatter(x=dfp["Tahun"], y=dfp["Skenario"] * (1 + pita), mode="lines", line=dict(width=0),
                                 showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=dfp["Tahun"], y=dfp["Skenario"] * (1 - pita), mode="lines", line=dict(width=0),
                                 fill="tonexty", fillcolor="rgba(15,82,186,0.12)", name="Rentang galat backtest"))
        fig.add_trace(go.Scatter(x=dfp["Tahun"], y=dfp["BAU"], name="Baseline (tren)", mode="lines+markers",
                                 line=dict(color=WARNA["bau"], width=2, dash="dash")))
        fig.add_trace(go.Scatter(x=dfp["Tahun"], y=dfp["Skenario"], name="Skenario", mode="lines+markers",
                                 line=dict(color=WARNA["simulasi"], width=3)))
        fig.update_xaxes(dtick=1)
        tampil(tata_letak(fig, "Gg CO₂e", 370))
    with g2:
        st.markdown("**Atribusi tuas kebijakan terhadap baseline (berurutan)**")
        at = hasil["atribusi"]
        nilai = [-at["labelling"], -at["elektrifikasi"], -at["grid"], -red30]
        fig_a = go.Figure(go.Waterfall(
            orientation="v", measure=["relative", "relative", "relative", "total"],
            x=["Efisiensi (labelling)", "Pergeseran LPG→listrik", "Dekarbonisasi grid", "Total vs baseline"], y=nilai,
            text=[fmt_tanda(v) for v in nilai], textposition="outside", cliponaxis=False,
            increasing={"marker": {"color": WARNA["naik"]}}, decreasing={"marker": {"color": WARNA["turun"]}},
            totals={"marker": {"color": WARNA["total"]}}))
        fig_a = tata_letak(fig_a, "Gg CO₂e", 370)
        fig_a.update_layout(hovermode="closest")
        tampil(fig_a)
        st.caption("Urutan penerapan: labelling → pergeseran bahan bakar → grid. Atribusi bergantung urutan karena ada interaksi (EF grid hanya menurunkan sisa listrik).")

    # LMDI atas lintasan
    st.markdown(f"**4. Dekomposisi LMDI {T1}–{T_PROY}**")
    l1, l2 = st.columns(2)
    h_bau = eg.lmdi_baris(F.loc[T1], hasil["rows_bau"][-1])
    h_sim = eg.lmdi_baris(F.loc[T1], hasil["rows_sim"][-1])
    with l1:
        st.markdown("Baseline (tren)")
        tampil(buat_waterfall(h_bau, 340))
    with l2:
        st.markdown("Skenario")
        tampil(buat_waterfall(h_sim, 340))
    selisih_efek = eg.lmdi_baris(hasil["rows_bau"][-1], hasil["rows_sim"][-1])
    ba, sa = ringkas_efek(h_sim)
    kotak(
        "Interpretasi (otomatis, bergantung skenario terpilih)",
        f"Pada skenario ini emisi {T_PROY} = <b>{fmt_id(c_sim30)} Gg</b>, "
        f"{'turun' if c_sim30 < c_last else 'naik'} <b>{fmt_id(abs(c_sim30 - c_last))} Gg</b> "
        f"({fmt_tanda((c_sim30 / c_last - 1) * 100, 1)}%) dibanding {T1}. Faktor pendorong kenaikan: {ba}. Faktor penahan: {sa}. "
        f"Dibanding baseline, kebijakan menggeser emisi {fmt_tanda(-red30)} Gg "
        f"(LMDI baseline→skenario: intensitas {fmt_tanda(selisih_efek['int'])}, bauran {fmt_tanda(selisih_efek['mix'])}, "
        f"faktor emisi {fmt_tanda(selisih_efek['ef'])} Gg; efek penduduk dan kemakmuran nol karena identik).",
        "hijau" if c_sim30 < c_last else "kuning",
    )

    ef_now = float(F.loc[T1, "EF_L"]) * eg.KONV_GWH_TJ
    ef_impas = eg.ef_impas_elektrifikasi(float(F.loc[T1, "EF_B"]), eta)
    kotak(
        "Catatan penting: elektrifikasi dapur bukan otomatis mitigasi",
        f"Dengan η = {eta:.2f}, memindahkan LPG ke listrik hanya menurunkan emisi bila EF listrik &lt; <b>{fmt_id(ef_impas, 2)} tCO₂/MWh</b>. "
        f"EF grid saat ini ≈ {fmt_id(ef_now, 2)}"
        + (f", dan bahkan pemangkasan 40% ({fmt_id(ef_now * 0.6, 2)}) masih di atas ambang. " if ef_now * 0.6 > ef_impas else ". ")
        + "Jadi, selama grid masih berbasis fosil, tuas ini menaikkan emisi Jakarta (di sisi pembangkit) — "
        "ini temuan yang relevan untuk kebijakan jargas/induksi dan dapat dibahas di skripsi.",
        "kuning",
    )

    st.markdown("**Sensitivitas terhadap pilihan sumber target (realisasi 100%, tanpa tuas lain)**")
    rows_s = []
    for nm, tg in eg.TARGET_LABEL.items():
        rr = eg.proyeksi(F.loc[T1], par_u, T_PROY, tg, 1.0, 0.0, 0.0, eta)["df"].iloc[-1]
        rows_s.append({"Sumber target": nm, f"Emisi {T_PROY} (Gg)": fmt_id(rr["Skenario"]),
                       f"vs {T1}": fmt_tanda((rr["Skenario"] / c_last - 1) * 100, 1) + "%",
                       "vs baseline (Gg)": fmt_tanda(rr["Skenario"] - rr["BAU"])})
    st.dataframe(pd.DataFrame(rows_s), hide_index=True, use_container_width=True)
    st.download_button("📥 Unduh lintasan skenario (CSV)", dfp.to_csv(index=False).encode("utf-8"),
                       "lintasan_skenario.csv", "text/csv")

# ==========================================================
# TAB 5 — ASUMSI & KETERBATASAN
# ==========================================================
with tab5:
    st.subheader("Asumsi dan Keterbatasan")
    st.markdown(
        f"""
**Cakupan.** Emisi energi rumah tangga (listrik tidak langsung + LPG/gas bumi langsung). Tidak mencakup limbah domestik dan air limbah rumah tangga, yang di inventarisasi DLH berada pada sektor Limbah.

**Dekomposisi.** LMDI-I aditif dua pembawa energi. Efek intensitas energi (E/Y) memakai PDRB total DKI sebagai pembagi sehingga memuat efisiensi *dan* perubahan struktur ekonomi; baca sebagai &lsquo;intensitas&rsquo;, bukan efisiensi murni. Mengganti ke pengeluaran konsumsi rumah tangga dan jumlah rumah tangga (bukan penduduk) adalah perbaikan yang direkomendasikan.

**Energi turunan.** E listrik tahun {T0}–{T1 - 1} diturunkan dari emisi/EF (belum dari GWh PLN). Faktor emisi listrik pasca-2019 di sumber sebagian bersifat asumsi data (lihat 4.1 butir 4), sehingga efek faktor emisi pasca-2019 tidak dapat dibaca sebagai capaian dekarbonisasi.

**Proyeksi.** Baseline adalah ekstrapolasi tren faktor, bukan prakiraan ekonometrik/teknologi. Backtest menunjukkan galat yang sebanding dengan besar efek kebijakan. Tuas EF grid dan η (efisiensi relatif listrik vs LPG) adalah **asumsi skenario**, bukan data laporan. Realisasi terkalibrasi adalah batas atas, bukan estimasi tak-bias.

**Tidak dimodelkan:** efek balik (*rebound*), biaya, kelayakan adopsi, dan faktor iklim. Menambahkan *cooling degree days* (BMKG) sebagai faktor keenam dalam identitas adalah perluasan paling relevan untuk Meteorologi Terapan: memisahkan efek suhu dari perilaku dan efisiensi (termasuk anomali 2020 dan tahun panas El Niño).

**Reproduksibilitas.** Seluruh data ada di `data_rt_dki.csv` (dengan kolom Status/Catatan); mesin hitung di `engine.py`; verifikasi dengan `python test_engine.py`.
"""
    )
