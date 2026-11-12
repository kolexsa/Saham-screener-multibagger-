import streamlit as st
import yfinance as yf
import pandas as pd
import feedparser

# Konfigurasi Halaman
st.set_page_config(page_title="Custom IDX Stock Screener", layout="wide")
st.title("📊 Custom Stock Screener & Strategy Analyzer")
st.markdown("Menganalisis saham berdasarkan **Prioritas PER, PBV, ROE, DER, Dividen Sektoral, Growth EPS, & Katalis Corporate Action**.")

# ==========================================
# 1. DAFTAR WATCHLIST SAHAM BEI
# ==========================================
DAFTAR_SAHAM = {
    "BBCA.JK": {"sektor": "Keuangan (Big Cap)", "cap_kategori": "Big Cap"},
    "BMRI.JK": {"sektor": "Keuangan (Big Cap)", "cap_kategori": "Big Cap"},
    "BBRI.JK": {"sektor": "Keuangan (Big Cap)", "cap_kategori": "Big Cap"},
    "ITMG.JK": {"sektor": "Batubara", "cap_kategori": "Mid Cap"},
    "ADRO.JK": {"sektor": "Batubara", "cap_kategori": "Big Cap"},
    "PTBA.JK": {"sektor": "Batubara", "cap_kategori": "Mid Cap"},
    "ASII.JK": {"sektor": "Otomotif & Konglomerasi", "cap_kategori": "Big Cap"},
    "ICBP.JK": {"sektor": "Konsumer", "cap_kategori": "Big Cap"},
    "CTRA.JK": {"sektor": "Properti (Lahan)", "cap_kategori": "Mid Cap"},
    "BSDE.JK": {"sektor": "Properti (Lahan)", "cap_kategori": "Mid Cap"},
}

# ==========================================
# 2. SIDEBAR: PENGATURAN PARAMETER STRATEGI
# ==========================================
st.sidebar.header("⚙️ Parameter Strategi Anda")
max_per = st.sidebar.slider("Batas Maksimal PER (Prioritas Utama)", 5, 30, 15)
max_pbv = st.sidebar.number_input("Target PBV Ideal (< 1)", value=1.0, step=0.1)
min_roe = st.sidebar.slider("Minimal ROE (%)", 5, 40, 15)
max_der = st.sidebar.slider("Maksimal DER (x)", 0.2, 3.0, 1.0, step=0.1)
min_div_coal = st.sidebar.slider("Min. Dividend Yield Batubara (%)", 3, 20, 8)

# ==========================================
# 3. MESIN ANALISIS & SKORING FUNDAMENTAL
# ==========================================
@st.cache_data(ttl=3600)
def ambil_dan_analisis_saham(tickers):
    hasil = []
    for ticker, meta in tickers.items():
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            harga = info.get("currentPrice", 0)
            per = info.get("trailingPE", None)
            pbv = info.get("priceToBook", None)
            roe = (info.get("returnOnEquity", 0) or 0) * 100
            der = (info.get("debtToEquity", 0) or 0) / 100
            div_yield = (info.get("dividendYield", 0) or 0) * 100
            market_cap = (info.get("marketCap", 0) or 0) / 1e12
            eps_growth = (info.get("earningsGrowth", 0) or 0) * 100

            # --- LOGIKA SKORING STRATEGI ANDA ---
            skor = 0
            catatan = []

            # Prioritas PER vs PBV
            if per is not None and 0 < per <= 10:
                skor += 30
                catatan.append("PER Sangat Murah (<=10)")
            elif per is not None and 10 < per <= max_per:
                skor += 20
                catatan.append(f"PER Bagus (<={max_per})")
            elif per is not None and per > max_per:
                catatan.append("PER Tinggi (Prioritas Turun)")

            if pbv is not None and 0 < pbv < max_pbv:
                skor += 15
                catatan.append("PBV < 1 (Undervalued)")

            # ROE > 15%
            if roe >= min_roe:
                skor += 20
                catatan.append(f"ROE Kuat ({roe:.1f}%)")

            # DER Kecil
            if 0 <= der <= max_der:
                skor += 15
                catatan.append(f"DER Sehat ({der:.2f}x)")

            # Dividen
            if meta["sektor"] == "Batubara":
                if div_yield >= min_div_coal:
                    skor += 10
                    catatan.append(f"Dividen Batubara Jumbo ({div_yield:.1f}%)")
            else:
                if div_yield > 0:
                    skor += 10
                    catatan.append(f"Rutin Dividen ({div_yield:.1f}%)")
                else:
                    catatan.append("⚠️ Tidak Bagi Dividen")

            # Growth EPS
            if eps_growth > 0:
                skor += 10
                catatan.append(f"EPS Tumbuh (+{eps_growth:.1f}%)")

            hasil.append({
                "Kode": ticker.replace(".JK", ""),
                "Sektor": meta["sektor"],
                "Market Cap (T)": round(market_cap, 2),
                "Harga (Rp)": harga,
                "PER (x)": round(per, 2) if per else 999,
                "PBV (x)": round(pbv, 2) if pbv else 999,
                "ROE (%)": round(roe, 2),
                "DER (x)": round(der, 2),
                "Div. Yield (%)": round(div_yield, 2),
                "EPS Growth (%)": round(eps_growth, 2),
                "Skor Strategi": skor,
                "Analisis Sistem": " | ".join(catatan)
            })
        except Exception:
            continue
            
    df = pd.DataFrame(hasil)
    return df.sort_values(by="Skor Strategi", ascending=False)

# ==========================================
# 4. PEMINDAI KATALIS CORPORATE ACTION
# ==========================================
def cek_corporate_action(kode_saham):
    url = f"https://news.google.com/rss/search?q={kode_saham}+saham+right+issue+OR+akuisisi+OR+lahan+OR+ekspansi&hl=id&gl=ID&ceid=ID:id"
    feed = feedparser.parse(url)
    katalis_ditemukan = []
    keywords = ["right issue", "akuisisi", "lahan", "ekspansi", "merger", "dividen", "kapasitas"]
    
    for entry in feed.entries[:5]:
        judul = entry.title
        if any(k in judul.lower() for k in keywords):
            katalis_ditemukan.append(f"• [{judul}]({entry.link})")
    return katalis_ditemukan

# ==========================================
# 5. TAMPILAN DASHBOARD (UI)
# ==========================================
tab1, tab2 = st.tabs(["🏆 Peringkat & Screener Saham", "🚀 Radar Corporate Action & Detail Emiten"])

with tab1:
    st.subheader("Hasil Penyaringan Berdasarkan Bobot Strategi Anda")
    with st.spinner("Mengambil data pasar & menghitung skor strategi..."):
        df_saham = ambil_dan_analisis_saham(DAFTAR_SAHAM)
    
    col1, col2 = st.columns(2)
    with col1:
        filter_sektor = st.multiselect("Filter Sektor:", options=df_saham["Sektor"].unique(), default=df_saham["Sektor"].unique())
    with col2:
        hanya_lolos = st.checkbox("Hanya tampilkan saham dengan Skor Strategi >= 60", value=False)

    df_tampil = df_saham[df_saham["Sektor"].isin(filter_sektor)]
    if hanya_lolos:
        df_tampil = df_tampil[df_tampil["Skor Strategi"] >= 60]

    st.dataframe(
        df_tampil.style.background_gradient(subset=["Skor Strategi"], cmap="Greens"),
        use_container_width=True,
        hide_index=True
    )

with tab2:
    st.subheader("Deteksi Katalis Corporate Action (Potensi Double Valuasi)")
    pilih_kode = st.selectbox("Pilih Kode Saham untuk Cek Katalis & Grafik:", df_saham["Kode"].tolist() if not df_saham.empty else ["BBCA"])
    
    col_kiri, col_kanan = st.columns([1, 1])
    
    with col_kiri:
        st.markdown(f"#### 📰 Berita & Katalis Aksi Korporasi: **{pilih_kode}**")
        st.caption("Mencari sinyal: *Right Issue, Penambahan Lahan, Akuisisi, & Ekspansi*")
        berita = cek_corporate_action(pilih_kode)
        if berita:
            for b in berita:
                st.markdown(b)
        else:
            st.info("Belum terdeteksi berita aksi korporasi besar dalam waktu dekat.")

    with col_kanan:
        st.markdown(f"#### 📈 Pergerakan Harga 1 Tahun: **{pilih_kode}**")
        hist = yf.Ticker(f"{pilih_kode}.JK").history(period="1y")
        if not hist.empty:
            st.line_chart(hist["Close"])
               
