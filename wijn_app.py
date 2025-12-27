import streamlit as st
import pandas as pd
import os
from fpdf import FPDF

# --- BESTANDSBEHEER ---
WINE_FILE = 'mijn_wijnen.csv'
ORDER_FILE = 'huidige_proeverij.csv'

def load_data(file, cols):
    if os.path.exists(file):
        return pd.read_csv(file)
    return pd.DataFrame(columns=cols)

# --- DE STAFFELKORTING LOGICA ---
def bereken_korting(totaal_flessen):
    # Jouw exacte staffel: [vanaf_aantal, gratis_flessen]
    staffel = [
        (60, 15), (54, 13), (48, 12), (42, 10), (36, 9), 
        (30, 7), (24, 6), (18, 4), (12, 3), (6, 1), (0, 0)
    ]
    for drempel, gratis in staffel:
        if totaal_flessen >= drempel:
            return gratis
    return 0

# --- UI CONFIGURATIE ---
st.set_page_config(page_title="Wijnproeverij Bestelbeheer", layout="wide")
st.title("🍷 Wijnproeverij Bestelbeheer")

# Laden van data
if 'df_wijnen' not in st.session_state:
    st.session_state.df_wijnen = load_data(WINE_FILE, ['Wijnnaam', 'Prijs'])
if 'df_orders' not in st.session_state:
    st.session_state.df_orders = load_data(ORDER_FILE, ['Naam', 'Wijnnaam', 'Aantal', 'Prijs_per_stuk'])

tab1, tab2, tab3 = st.tabs(["📋 Bestellen", "📊 Totaaloverzicht", "⚙️ Assortiment Beheren"])

# --- TAB 3: ASSORTIMENT BEHEREN ---
with tab3:
    st.header("Wijnen & Prijzen")
    st.info("Wijzigingen in deze tabel worden direct opgeslagen in je database.")
    
    # Gebruik de data_editor voor toevoegen en aanpassen
    edited_wijnen = st.data_editor(st.session_state.df_wijnen, num_rows="dynamic", key="wine_editor")
    
    if st.button("💾 Database Opslaan"):
        st.session_state.df_wijnen = edited_wijnen
        edited_wijnen.to_csv(WINE_FILE, index=False)
        st.success("Wijnlijst bijgewerkt!")

# --- TAB 1: BESTELLEN ---
with tab1:
    st.header("Nieuwe Bestelling Invoeren")
    if st.session_state.df_wijnen.empty:
        st.warning("Voeg eerst wijnen toe in het tabblad 'Assortiment Beheren'.")
    else:
        with st.form("order_form", clear_on_submit=True):
            col1, col2, col3 = st.columns([2, 2, 1])
            naam_klant = col1.text_input("Naam Persoon")
            wijn_keuze = col2.selectbox("Kies Wijn", st.session_state.df_wijnen['Wijnnaam'].tolist())
            aantal = col3.number_input("Aantal flessen", min_value=1, step=1)
            
            if st.form_submit_button("Toevoegen"):
                # Haal huidige prijs op uit database
                prijs = st.session_state.df_wijnen[st.session_state.df_wijnen['Wijnnaam'] == wijn_keuze]['Prijs'].values[0]
                nieuwe_order = pd.DataFrame([[naam_klant, wijn_keuze, aantal, prijs]], 
                                           columns=['Naam', 'Wijnnaam', 'Aantal', 'Prijs_per_stuk'])
                st.session_state.df_orders = pd.concat([st.session_state.df_orders, nieuwe_order], ignore_index=True)
                st.session_state.df_orders.to_csv(ORDER_FILE, index=False)
                st.toast(f"Toegevoegd: {aantal}x {wijn_keuze} voor {naam_klant}")

    st.subheader("Bestellingen van deze avond")
    st.dataframe(st.session_state.df_orders, use_container_width=True)
    if st.button("🗑️ Wis hele proeverij (Nieuwe Start)"):
        st.session_state.df_orders = pd.DataFrame(columns=['Naam', 'Wijnnaam', 'Aantal', 'Prijs_per_stuk'])
        if os.path.exists(ORDER_FILE): os.remove(ORDER_FILE)
        st.rerun()

# --- TAB 2: TOTAALOVERZICHT ---
with tab2:
    st.header("Eindafrekening & Korting")
    if not st.session_state.df_orders.empty:
        df = st.session_state.df_orders.copy()
        df['Totaal'] = df['Aantal'] * df['Prijs_per_stuk']
        
        # Groepsstatistieken
        totaal_flessen_groep = df['Aantal'].sum()
        gratis_flessen = bereken_korting(totaal_flessen_groep)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Totaal bestelde flessen", totaal_flessen_groep)
        c2.metric("🎁 Gratis flessen verdiend", gratis_flessen)
        c3.metric("Totaalbedrag Groep", f"€ {df['Totaal'].sum():.2f}")

        st.divider()

        # Per persoon overzicht
        per_persoon = df.groupby('Naam').agg({'Aantal': 'sum', 'Totaal': 'sum'}).reset_index()
        st.subheader("Overzicht per persoon (voor screenshot)")
        st.table(per_persoon.style.format({"Totaal": "€ {:.2f}"}))
        
        # PDF Export (Basis)
        if st.button("📄 Genereer PDF (Download)"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt="Besteloverzicht Wijnproeverij", ln=True, align='C')
            pdf.set_font("Arial", size=12)
            pdf.ln(10)
            for _, row in per_persoon.iterrows():
                pdf.cell(200, 10, txt=f"{row['Naam']}: {row['Aantal']} flessen - Totaal: €{row['Totaal']:.2f}", ln=True)
            pdf.ln(10)
            pdf.cell(200, 10, txt=f"Totaal Groep: {totaal_flessen_groep} flessen", ln=True)
            pdf.cell(200, 10, txt=f"Gratis flessen verdiend door groep: {gratis_flessen}", ln=True)
            
            pdf_output = pdf.output(dest='S').encode('latin-1')
            st.download_button(label="Klik hier om PDF te downloaden", data=pdf_output, file_name="wijn_bestelling.pdf", mime="application/pdf")
    else:
        st.write("Nog geen bestellingen ingevoerd.")
