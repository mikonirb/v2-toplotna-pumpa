import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Konfiguracija stranice
st.set_page_config(page_title="TP Monitor", layout="wide", page_icon="🔥")

# Ime fajla za čuvanje podataka
DATA_FILE = "toplotna_pumpa_data.csv"

# --- FUNKCIJE ---

def load_data():
    """Učitava podatke iz CSV fajla."""
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df['Datum'] = pd.to_datetime(df['Datum'])
        return df.sort_values(by='Datum')
    else:
        return pd.DataFrame(columns=[
            'Datum', 'Brojilo_1_Stanje', 'Brojilo_2_Stanje', 
            'Aktivno_Brojilo', 'TP_Proizvedeno_kWh', 
            'Kompresor_Sati', 'Pumpa_Sati', 'Ciklusi', 'LWT_Temp'
        ])

def save_data(data):
    """Čuva podatke u CSV fajl."""
    # Ako fajl ne postoji, upisujemo header, inače samo dodajemo red
    if not os.path.exists(DATA_FILE):
        pd.DataFrame([data]).to_csv(DATA_FILE, index=False)
    else:
        pd.DataFrame([data]).to_csv(DATA_FILE, mode='a', header=False, index=False)

# --- GLAVNI INTERFEJS ---

st.title("🔥 Praćenje Efikasnosti Toplotne Pumpe")

# Meni u sidebaru
menu = st.sidebar.radio("Navigacija", ["Unos Podataka", "Analiza i Grafikoni", "Sirovi Podaci"])

# ----------------- UNOS PODATAKA -----------------
if menu == "Unos Podataka":
    st.header("📝 Unos novog stanja")
    
    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            datum = st.date_input("Datum očitavanja", datetime.now())
            brojilo_1 = st.number_input("Stanje Brojila 1 (kWh)", min_value=0.0, format="%.2f")
            brojilo_2 = st.number_input("Stanje Brojila 2 (kWh)", min_value=0.0, format="%.2f")
            aktivno = st.selectbox("Koje brojilo trenutno meri TP?", ["Brojilo 1", "Brojilo 2"])
            
        with col2:
            tp_proizvedeno = st.number_input("TP Proizvedena energija (Thermal kWh)", min_value=0.0, format="%.1f")
            lwt = st.number_input("LWT (Izlazna temp vode) °C", min_value=0.0, max_value=80.0, format="%.1f")
            kompresor_h = st.number_input("Rad kompresora (sati)", min_value=0, step=1)
            pumpa_h = st.number_input("Rad cirkulacione pumpe (sati)", min_value=0, step=1)
            ciklusi = st.number_input("Broj ciklusa kompresora", min_value=0, step=1)

        submitted = st.form_submit_button("💾 Sačuvaj Podatke")
        
        if submitted:
            new_entry = {
                'Datum': datum,
                'Brojilo_1_Stanje': brojilo_1,
                'Brojilo_2_Stanje': brojilo_2,
                'Aktivno_Brojilo': aktivno,
                'TP_Proizvedeno_kWh': tp_proizvedeno,
                'Kompresor_Sati': kompresor_h,
                'Pumpa_Sati': pumpa_h,
                'Ciklusi': ciklusi,
                'LWT_Temp': lwt
            }
            save_data(new_entry)
            st.success("Podaci su uspešno sačuvani!")

# ----------------- ANALIZA -----------------
elif menu == "Analiza i Grafikoni":
    st.header("📊 Analiza Sezone Grejanja")
    
    df = load_data()
    
    if df.empty or len(df) < 2:
        st.warning("Potrebno je uneti bar dva unosa (dva dana) da bi se izračunala potrošnja i COP.")
    else:
        # --- KALKULACIJE ---
        # Računamo razliku (deltu) u odnosu na prethodni unos
        df['Delta_Dana'] = df['Datum'].diff().dt.days
        df['Potrosnja_B1'] = df['Brojilo_1_Stanje'].diff()
        df['Potrosnja_B2'] = df['Brojilo_2_Stanje'].diff()
        df['Proizvedeno_Delta'] = df['TP_Proizvedeno_kWh'].diff()
        
        # Logika za aktivno brojilo: Uzimamo potrošnju onog brojila koje je bilo aktivno
        # (Pojednostavljeno: uzimamo ono koje je označeno u trenutnom redu)
        df['Potrosnja_Ukupna'] = df.apply(
            lambda x: x['Potrosnja_B1'] if x['Aktivno_Brojilo'] == 'Brojilo 1' else x['Potrosnja_B2'], axis=1
        )
        
        # Filtriramo prvi red jer je on NaN nakon diff-a
        df_clean = df.dropna(subset=['Potrosnja_Ukupna', 'Proizvedeno_Delta'])
        
        # --- METRIKE ---
        st.subheader("Pregled performansi")
        
        # Opcija za "čišćenje" potrošnje domaćinstva
        # Pošto brojilo meri i kuću, COP će biti manji. Ovde možemo oduzeti procenjenu potrošnju kuće.
        st.info("💡 Pošto brojilo meri i ostale uređaje, unesite procenu dnevne potrošnje kuće (bez TP) za precizniji COP.")
        fiksna_potrosnja_kuce = st.slider("Procenjena potrošnja kuće (kWh/dan)", 0, 20, 8)
        
        df_clean['Potrosnja_Samo_TP'] = df_clean['Potrosnja_Ukupna'] - (fiksna_potrosnja_kuce * df_clean['Delta_Dana'])
        # Zaštita od negativnih brojeva
        df_clean['Potrosnja_Samo_TP'] = df_clean['Potrosnja_Samo_TP'].clip(lower=0.1) 
        
        df_clean['COP'] = df_clean['Proizvedeno_Delta'] / df_clean['Potrosnja_Samo_TP']
        
        # Prikaz KPI kartica (prosek zadnjih 7 unosa ili sve)
        avg_cop = df_clean['COP'].mean()
        total_heat = df_clean['Proizvedeno_Delta'].sum()
        total_elec = df_clean['Potrosnja_Ukupna'].sum()
        
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Prosečan COP (procenjen)", f"{avg_cop:.2f}")
        kpi2.metric("Ukupno Proizvedeno (Toplota)", f"{total_heat:.0f} kWh")
        kpi3.metric("Ukupno Potrošeno (Struja)", f"{total_elec:.0f} kWh")

        # --- GRAFIKONI ---
        
        tab1, tab2, tab3 = st.tabs(["COP & Efikasnost", "Temperature & Ciklusi", "Sati Rada"])
        
        with tab1:
            st.markdown("### Odnos Potrošene i Proizvedene Energije")
            fig_energy = go.Figure()
            fig_energy.add_trace(go.Bar(x=df_clean['Datum'], y=df_clean['Potrosnja_Ukupna'], name='Potrošnja Struje (Ukupno)'))
            fig_energy.add_trace(go.Bar(x=df_clean['Datum'], y=df_clean['Proizvedeno_Delta'], name='Proizvedena Toplota'))
            st.plotly_chart(fig_energy, use_container_width=True)
            
            st.markdown("### Trend COP-a")
            fig_cop = px.line(df_clean, x='Datum', y='COP', markers=True, title="Coefficient of Performance (Dnevni)")
            # Dodaj liniju za COP = 3 (referenca)
            fig_cop.add_hline(y=3, line_dash="dash", line_color="green", annotation_text="Dobar COP (3.0)")
            st.plotly_chart(fig_cop, use_container_width=True)

        with tab2:
            st.markdown("### Izlazna Temperatura (LWT) vs Ciklusi")
            fig_temp = px.scatter(df_clean, x='LWT_Temp', y='Ciklusi', color='COP', size='Potrosnja_Ukupna', 
                                title="Zavisnost Ciklusa od Temperature (Boja = COP)")
            st.plotly_chart(fig_temp, use_container_width=True)

        with tab3:
            st.markdown("### Rad Kompresora i Pumpe")
            # Ovde nam trebaju delte sati rada, ne ukupni
            df_clean['Kompresor_Delta'] = df['Kompresor_Sati'].diff()
            df_clean['Pumpa_Delta'] = df['Pumpa_Sati'].diff()
            
            fig_hours = go.Figure()
            fig_hours.add_trace(go.Scatter(x=df_clean['Datum'], y=df_clean['Kompresor_Delta'], mode='lines+markers', name='Sati Kompresora'))
            fig_hours.add_trace(go.Scatter(x=df_clean['Datum'], y=df_clean['Pumpa_Delta'], mode='lines+markers', name='Sati Pumpe'))
            st.plotly_chart(fig_hours, use_container_width=True)

# ----------------- SIROVI PODACI -----------------
elif menu == "Sirovi Podaci":
    st.header("🗃️ Pregled Baze Podataka")
    df = load_data()
    st.dataframe(df)
    
    st.download_button(
        label="Preuzmi CSV",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name='toplotna_pumpa_export.csv',
        mime='text/csv',
    )
