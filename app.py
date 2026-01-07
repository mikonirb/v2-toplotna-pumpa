import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Konfiguracija stranice
st.set_page_config(page_title="TP Monitor", layout="wide", page_icon="🔥")

st.title("🔥 Praćenje Efikasnosti Toplotne Pumpe")

# --- POVEZIVANJE SA GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(ttl="0")
        if df is None or df.empty:
            return pd.DataFrame()
        
        df.columns = df.columns.str.strip()
        df['Datum'] = pd.to_datetime(df['Datum'], errors='coerce')
        
        numeric_cols = [
            'Brojilo_1_Stanje', 'Brojilo_2_Stanje', 'TP_Proizvedeno_kWh', 
            'Kompresor_Sati', 'Pumpa_Sati', 'Ciklusi', 'LWT_Temp'
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = df.dropna(subset=['Datum'])
        return df.sort_values(by='Datum')
    except Exception as e:
        st.error(f"Greška pri čitanju Sheets-a: {e}")
        return pd.DataFrame()

# --- POMOĆNA FUNKCIJA ZA RESET BROJAČA ---
def calculate_delta(series):
    """Računa razliku, ali rešava problem reseta brojača na nulu."""
    diff = series.diff()
    # Ako je diff negativan, znači da se desio reset. 
    # U tom slučaju, trenutna vrednost je zapravo naš delta od nule.
    return diff.mask(diff < 0, series)

# --- GLAVNI INTERFEJS ---
menu = st.sidebar.radio("Navigacija", ["Unos Podataka", "Analiza i Grafikoni", "Sirovi Podaci"])

if menu == "Unos Podataka":
    st.header("📝 Unos novog stanja")
    df_existing = load_data()
    
    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            datum = st.date_input("Datum očitavanja", datetime.now())
            brojilo_1 = st.number_input("Stanje Brojila 1 (kWh)", min_value=0.0, format="%.2f")
            brojilo_2 = st.number_input("Stanje Brojila 2 (kWh)", min_value=0.0, format="%.2f")
            aktivno = st.selectbox("Koje brojilo trenutno meri TP?", ["Brojilo 1", "Brojilo 2"])
        with col2:
            tp_proizvedeno = st.number_input("TP Proizvedena energija (Thermal kWh)", min_value=0.0, format="%.1f")
            lwt = st.number_input("LWT °C", min_value=0.0, max_value=80.0, format="%.1f")
            kompresor_h = st.number_input("Rad kompresora (sati)", min_value=0, step=1)
            pumpa_h = st.number_input("Rad cirkulacione pumpe (sati)", min_value=0, step=1)
            ciklusi = st.number_input("Broj ciklusa", min_value=0, step=1)

        submitted = st.form_submit_button("💾 Sačuvaj u Google Sheets")
        
        if submitted:
            new_row = pd.DataFrame([{
                'Datum': datum.strftime('%Y-%m-%d'),
                'Brojilo_1_Stanje': brojilo_1,
                'Brojilo_2_Stanje': brojilo_2,
                'Aktivno_Brojilo': aktivno,
                'TP_Proizvedeno_kWh': tp_proizvedeno,
                'Kompresor_Sati': kompresor_h,
                'Pumpa_Sati': pumpa_h,
                'Ciklusi': ciklusi,
                'LWT_Temp': lwt
            }])
            
            df_updated = pd.concat([df_existing, new_row], ignore_index=True) if not df_existing.empty else new_row
            conn.update(data=df_updated)
            st.success("Podaci upisani!")
            st.balloons()

elif menu == "Analiza i Grafikoni":
    st.header("📊 Analiza Sezone Grejanja")
    df = load_data()
    
    if df.empty or len(df) < 2:
        st.warning("Potrebno je uneti bar dva očitavanja.")
    else:
        # Primena logike za reset brojača
        df['Delta_Dana'] = df['Datum'].diff().dt.total_seconds().fillna(0) / (24 * 3600)
        df['Potrosnja_B1'] = calculate_delta(df['Brojilo_1_Stanje']).fillna(0)
        df['Potrosnja_B2'] = calculate_delta(df['Brojilo_2_Stanje']).fillna(0)
        df['Proizvedeno_Delta'] = calculate_delta(df['TP_Proizvedeno_kWh']).fillna(0)
        
        df['Potrosnja_Ukupna'] = df.apply(
            lambda x: x['Potrosnja_B1'] if x['Aktivno_Brojilo'] == 'Brojilo 1' else x['Potrosnja_B2'], axis=1
        )
        
        df_clean = df.iloc[1:].copy()
        
        # Podešavanje potrošnje domaćinstva
        fiksna_potrosnja_kuce = st.slider("Dnevna potrošnja kuće bez TP (kWh/dan)", 0.0, 30.0, 10.0, step=0.5)
        df_clean['Potrosnja_Samo_TP'] = (df_clean['Potrosnja_Ukupna'] - (fiksna_potrosnja_kuce * df_clean['Delta_Dana'])).clip(lower=0.5)
        
        # Računanje COP-a uz izbegavanje nerealnih vrednosti pri resetu
        df_clean['COP'] = (df_clean['Proizvedeno_Delta'] / df_clean['Potrosnja_Samo_TP']).replace([float('inf'), -float('inf')], 0).fillna(0)
        # Ograničavamo COP na razuman opseg (npr. max 8) da grafikon ne poludi
        df_clean['COP'] = df_clean['COP'].clip(upper=8.0, lower=0.0)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Prosečan COP", f"{df_clean['COP'].mean():.2f}")
        c2.metric("Ukupna Toplota (period)", f"{df_clean['Proizvedeno_Delta'].sum():.0f} kWh")
        c3.metric("Ukupna Struja (period)", f"{df_clean['Potrosnja_Ukupna'].sum():.0f} kWh")

        tab1, tab2 = st.tabs(["Efikasnost", "Parametri Rada"])
        with tab1:
            fig_en = px.area(df_clean, x='Datum', y=['Proizvedeno_Delta', 'Potrosnja_Ukupna'], 
                             title="Proizvedena vs Potrošena Energija (korigovano za reset)", 
                             labels={'value': 'kWh', 'variable': 'Tip energije'})
            st.plotly_chart(fig_en, use_container_width=True)
            
            fig_cop = px.line(df_clean, x='Datum', y='COP', markers=True, title="Trend COP-a")
            fig_cop.add_hline(y=3, line_dash="dash", line_color="green")
            st.plotly_chart(fig_cop, use_container_width=True)
            
        with tab2:
            df_clean['Kompresor_D'] = calculate_delta(df['Kompresor_Sati']).iloc[1:].fillna(0)
            st.plotly_chart(px.bar(df_clean, x='Datum', y='Kompresor_D', title="Sati rada kompresora po periodu"), use_container_width=True)

elif menu == "Sirovi Podaci":
    st.header("🗃️ Podaci iz Google Sheets-a")
    df = load_data()
    st.dataframe(df)
