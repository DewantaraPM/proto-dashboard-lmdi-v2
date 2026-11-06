"""
Dashboard hasil magang — Inventarisasi GRK & Capaian Mitigasi DKI Jakarta (data: Laporan Akhir DLH 2026)
Jalankan lokal:  streamlit run app.py
Data dibaca dari folder data/ (dibuat oleh siapkan_data.py dari Excel hasil ekstraksi tabel laporan).
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
DATA = Path(__file__).parent / "data"


@st.cache_data
def muat():
    return {
        "bi": pd.read_csv(DATA / "baseline_inventori.csv"),
        "sek": pd.read_csv(DATA / "emisi_sektor.csv"),
        "aksi": pd.read_csv(DATA / "capaian_aksi_2025.csv"),
        "tgt": pd.read_csv(DATA / "target_aksi_2025_2030.csv"),
        "kk": pd.read_csv(DATA / "kategori_kunci_2025.csv"),
        "cek": pd.read_csv(DATA / "pemeriksaan.csv"),
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
