Analisis Komprehensif: Web App Backtesting Simulator

Peran: Senior Frontend Engineer & UX Researcher
Fokus Utama: Replikasi fungsi baseline & Integrasi Skenario Profil Risiko

1. Arsitektur Layout & UI (User Interface)

Struktur Tata Letak:

Aplikasi menggunakan Single-Column Layout yang dibungkus dalam kontainer max-width (berpusat di tengah layar) dengan margin yang lega.

Navigasi menggunakan Top Navigation Bar yang sangat minimalis (hanya berisi judul aplikasi, tombol toggle halaman "Backtesting", dan info pembaruan data).

Konten dibagi ke dalam Card/Panel yang dirender secara vertikal: Panel Input Parameter -> Panel Metrik Ringkasan -> Panel Chart Ekuitas -> Panel Chart Indikator -> Tabel Riwayat.

Skema Warna (Color Palette) — NEO-BRUTALIST "DIGITAL CURATOR":

Tema: Dark Mode pekat dengan estetika Neo-Brutalist.

Background Utama: #0F1117 (Streamlit dark) / #060810 (sidebar).

Background Card: #0a0c10 untuk metric cards, #0d1117 untuk nav cards.

Warna Aksen/Semantik:
- Brand/Primary: Teal-green #00D4AA (digunakan untuk hard shadows, border highlights, dan tombol utama).
- Positive/Buy: Hijau terang #22C55E.
- Negative/Sell: Merah terang #EF4444.
- Teks: #E5E7EB untuk hierarki utama, abu-abu redup untuk label/sekunder.

Prinsip Desain — NEO-BRUTALIST:

1. Hard Shadow (bukan soft blur): Setiap elemen terangkat menggunakan shadow keras "4px 4px 0px 0px" — meniru objek fisik yang melempar bayangan di atas meja.
2. Zero Border-Radius: Semua komponen (cards, buttons, badges, tables, expanders) menggunakan border-radius: 0px. Sistem ini didefinisikan oleh sudut 90-derajat.
3. 2px Borders: Tidak ada garis tipis 1px; semua border menggunakan 2px solid untuk keterbacaan struktural.
4. Tactile Buttons: Tombol menggunakan translate(-2px, -2px) saat hover dan translate(2px, 2px) saat active — memberikan efek "mechanical click" yang memuaskan.

Tipografi — DUAL FONT STACK:

- Display & Headline: Space Grotesk (dari Google Fonts) — sans-serif geometris untuk heading dan nilai metrik besar.
- Title & Body: Work Sans — high-performance sans-serif untuk teks data dan label.
- Labels & Metadata: Inter — untuk label teknis dan tag uppercase.

Hierarki Editorial: Gunakan angka besar (display-lg) sebagai hero layar, diikuti label kecil uppercase. Kontras "High-Low" ini memisahkan dashboard dari dokumen biasa.

Jenis Komponen UI yang Terlihat:

Input Panel: Number Input Box, Date Picker modern, Range Slider, Primary Button (teal gradient dengan hard shadow).
Output Panel: Metric Cards dengan hard shadow teal, angka display-lg (Space Grotesk), label uppercase kecil.
Visualisasi: Interactive Plotly Charts (Line & Area), Data Tables dengan border 2px dan hard shadow.
Badges & Alerts: 2px border, 0px radius, warna semantik (amber untuk warning, red untuk error, teal untuk info).

2. Analisis Fitur & Interaksi (UX)

Panel Input (Simulation Parameters)

Pengguna memiliki kontrol penuh terhadap parameter berikut:

Modal Awal (USD): Number input (di video diubah dari 10.000 menjadi 500).

Periode Mulai: Date picker (Batas bawah rentang kalender simulasi).

Periode Akhir: Date picker (Batas atas rentang kalender simulasi).

Buy Threshold (Trolololo <= %): Slider persentase. Mengontrol titik di mana indikator memicu sinyal beli (di video diset dari 25% ke 5%).

Sell Threshold (Trolololo >= %): Slider persentase. Mengontrol titik sinyal jual (di video diset dari 75% ke 23%).

Alokasi Beli (% dari Cash): Slider persentase (1% - 100%).

Alokasi Jual (% dari BTC): Slider persentase (1% - 100%).

Panel Output (Kartu Metrik)

Setelah simulasi dijalankan, sistem merender 7 metrik utama:

Portfolio Akhir: Nilai tunai total akhir + Persentase Return (Total Return).

HODL Comparison: Nilai akhir jika pengguna hanya membeli dan menahan (B&H) sejak tanggal mulai.

Max Drawdown: Risiko sisi bawah maksimum dalam persentase (Negatif).

Total Trades: Total transaksi, di- breakdown menjadi X Buys dan Y Sells.

Sisa Cash: Uang tunai yang belum dibelikan aset.

Sisa BTC: Jumlah aset yang dipegang di akhir periode.

Strategy vs HODL: Selisih nominal USD antara strategi dan benchmark B&H.

Interaktivitas & State Management

Sistem Eksekusi Eksplisit: Grafik dan metrik TIDAK berubah secara real-time (on-change) saat slider digeser. Pengguna harus menekan tombol "Jalankan Simulasi" agar data diperbarui.

Kinerja Cepat: Tidak terlihat loading spinner yang mencolok (hanya sedikit flicker data transfer di browser), menunjukkan bahwa kalkulasi backtesting di-handle dengan sangat cepat di backend (kemungkinan menggunakan operasi vektor Pandas) lalu dikembalikan ke frontend.

3. Analisis Visualisasi Data (Charting)

Terdapat dua grafik interaktif utama pada halaman simulator:

Equity Curve (Kurva Ekuitas):

Sumbu X: Waktu (Tanggal).

Sumbu Y: Nilai Portofolio (USD).

Seri Data: Garis Oranye (HODL Equity) dan Garis bergradasi/dua warna (Strategy Equity - Hijau saat menang, Merah saat drawdown).

Overlay Tambahan: Penanda eksplisit (markers) berupa Segitiga Hijau untuk titik transaksi BUY dan Segitiga Merah untuk SELL.

Trolololo Index with Signals (Ini akan Anda ganti dengan CBBI):

Sumbu X: Waktu (Tanggal).

Sumbu Y: Nilai Indeks (0% - 100%).

Seri Data: Garis Kuning (Nilai Indeks).

Overlay Tambahan: Garis putus-putus Hijau horizontal (batas Buy Threshold) dan garis putus-putus Merah horizontal (batas Sell Threshold).

Fungsi Interaktif: Kedua grafik sangat interaktif. Terdapat fitur hover tooltip canggih yang menampilkan nilai persis (harga, ekuitas, status beli/jual) pada tanggal kursor berada. Grafik ini hampir pasti merender ulang (re-render) penanda panah beli/jual dan garis putus-putus setiap kali simulasi baru dijalankan.

4. Estimasi Framework & Tech Stack

Berdasarkan analisis visual dan respons UI:

Frontend Framework (Highly Likely): React.js (Next.js/Vite) atau Vue.js (Nuxt)

Alasan: Tampilan sangat terpoles (polished). Komponen slider, date picker, dan kartu memiliki gaya yang konsisten yang sulit didapat langsung dari framework pure-Python seperti Streamlit tanpa custom CSS/HTML yang sangat masif (hampir merombak seluruh DOM-nya). Interaksi form dan rendering ulang komponen terasa seperti SPA (Single Page Application).

Alternatif (Jika murni Python): Jika profesor Anda murni menggunakan Python, ini kemungkinan dibangun menggunakan Dash (Plotly) dengan styling CSS eksternal yang sangat kustom, atau framework baru seperti Taipy / FasHTML. Tampilan ini bukan tampilan default Streamlit.

Pustaka Visualisasi Charting: Plotly.js atau Apache ECharts

Alasan: Perilaku hover tooltip komprehensif, kemampuan zoom/pan (meski tidak dilakukan di video, feel-nya ada), dan gaya overlay penanda panah sangat khas dari Plotly atau ECharts yang umum dipasangkan dengan backend Python pengolah data keuangan.

Backend Estimasi: Python (FastAPI/Flask) menggunakan pustaka Pandas/Numpy terkompilasi untuk engine backtesting berkecepatan tinggi.

5. Rekomendasi Integrasi Fitur "Profil Risiko" (Berdasarkan PRD Anda)

Berdasarkan arsitektur video, Anda memiliki cukup ruang di dalam card "Simulation Parameters". Berikut rancangan UX integrasinya:

Posisi Paling Intuitif

Letakkan komponen "Skenario Profil Risiko (Presets)" di baris paling atas di dalam card Simulation Parameters, tepat di atas row input "Modal Awal / Periode".

Bentuk Komponen UI

Gunakan kelompok tombol datar (Toggle Button Group) atau kotak Dropdown besar berlabel: "Muat Parameter Optimal Hasil Penelitian:"

Opsi yang tersedia (sesuai PRD):

Custom (Bebas) -> Default state

Skenario 1: Max Return (IS/OOS)

Skenario 1: Min Drawdown

Skenario 2: Eksplorasi Maksimal (Full)

Rancang Alur Interaksi (UX Flow)

Agar mengakomodasi tujuan penelitian sekaligus mempertahankan kebebasan pengguna seperti web aslinya, terapkan logika State Management berikut:

Pilih Preset: Pengguna mengklik tombol "Skenario 1: Max Return".

Auto-Fill (Animasi): Slider untuk "Buy Threshold", "Sell Threshold", "Alokasi Beli", dan "Alokasi Jual" secara otomatis bergeser ke angka optimal hasil riset Anda.

Visual Cue: Berikan indikator visual singkat (misal: outline hijau atau toast notification) yang menyatakan "Parameter Optimal Max Return dimuat".

Date Locking (Opsional tapi Direkomendasikan): Jika pengguna memilih preset Skenario 1, kunci (disable) atau paksa Date Picker ke periode evaluasi Anda (misal Skenario 1 OOS: 2021-2026) agar hasil di layar match dengan di laporan Anda.

Reverting to Custom: JANGAN disable slider setelah preset dipilih. Biarkan slider tetap aktif. Namun, jika setelah memilih Skenario, pengguna sengaja menggeser slider lagi, ubah status Dropdown/Toggle kembali ke Custom (Bebas) secara otomatis. Ini memberikan sinyal ke pengguna bahwa mereka kini keluar dari jalur aman rekomendasi riset Anda.