import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import plotly.express as px
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Nutri-Soutien Pro", page_icon="🥗", layout="wide")
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>""", unsafe_allow_html=True)

def init_db():
    conn = sqlite3.connect('nutri_data_v2.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY, nom TEXT, prenom TEXT, 
                phone TEXT, password TEXT, sex TEXT, pays TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS collectes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_email TEXT, 
                date TEXT, patient TEXT, poids REAL, taille REAL, imc REAL, statut TEXT)''')
    conn.commit()
    return conn, c

conn, c = init_db()

def hash_pwd(pwd):
    return hashlib.sha256(str.encode(pwd)).hexdigest()

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_info = None

def main():
    if not st.session_state.authenticated:
        # --- LOGIQUE DE CONNEXION ---
        st.title("🥗 Nutri-Soutien")
        choix = st.radio("Option :", ["Se connecter", "S'inscrire"], horizontal=True)
        
        if choix == "S'inscrire":
            with st.form("inscription"):
                n, p, e, pw = st.text_input("Nom"), st.text_input("Prénom"), st.text_input("Email"), st.text_input("Mot de passe", type='password')
                if st.form_submit_button("S'inscrire"):
                    try:
                        c.execute('INSERT INTO users VALUES (?,?,?,?,?,?,?)', (e, n, p, "", hash_pwd(pw), "", ""))
                        conn.commit()
                        st.success("Compte créé !")
                    except: st.error("Erreur.")
        else:
            with st.form("login"):
                l_n, l_p, l_pw = st.text_input("Nom"), st.text_input("Prénom"), st.text_input("Mot de passe", type='password')
                if st.form_submit_button("Connexion"):
                    c.execute('SELECT * FROM users WHERE nom=? AND prenom=? AND password=?', (l_n, l_p, hash_pwd(l_pw)))
                    user = c.fetchone()
                    if user:
                        st.session_state.authenticated, st.session_state.user_info = True, user
                        st.rerun()

    else:
        u_email = st.session_state.user_info[0]
        st.sidebar.title(f"👤 {st.session_state.user_info[2]}")
        menu = st.sidebar.selectbox("Navigation", ["Collecte & Gestion", "Déconnexion"])

        if menu == "Déconnexion":
            st.session_state.authenticated = False
            st.rerun()

        elif menu == "Collecte & Gestion":
            st.header("📋 Gestion des données patients")
            tab_saisie, tab_histo, tab_modif = st.tabs(["📥 Saisie", "📊 Archives & Graphique", "🛠️ Modifier/Supprimer"])
            
            # --- ONGLET 1 : SAISIE ---
            with tab_saisie:
                with st.form("form_saisie"):
                    p_nom = st.text_input("Nom du Patient")
                    poids = st.number_input("Poids (kg)", 1.0, 250.0, 70.0)
                    taille = st.number_input("Taille (cm)", 50, 250, 170)
                    if st.form_submit_button("Sauvegarder"):
                        imc = round(poids / ((taille/100)**2), 2)
                        statut = "Normal" if 18.5 <= imc < 25 else "Alerte"
                        c.execute('INSERT INTO collectes (user_email, date, patient, poids, taille, imc, statut) VALUES (?,?,?,?,?,?,?)',
                                 (u_email, datetime.now().strftime("%d/%m/%Y"), p_nom, poids, taille, imc, statut))
                        conn.commit()
                        st.success(f"Données de {p_nom} enregistrées.")

            # --- ONGLET 2 : ARCHIVES & GRAPHIQUE ---
            with tab_histo:
                c.execute('SELECT date, patient, imc, statut FROM collectes WHERE user_email=?', (u_email,))
                rows = c.fetchall()
                if rows:
                    df = pd.DataFrame(rows, columns=["Date", "Patient", "IMC", "Statut"])
                    col_t, col_g = st.columns(2)
                    with col_t: st.dataframe(df, use_container_width=True)
                    with col_g:
                        fig = px.pie(df, names='Statut', hole=0.4, color='Statut',
                                     color_discrete_map={'Normal':'#2ecc71', 'Alerte':'#e74c3c'})
                        st.plotly_chart(fig, use_container_width=True)
                else: st.info("Aucune donnée.")

            # --- ONGLET 3 : MODIFIER / SUPPRIMER ---
            with tab_modif:
                st.subheader("Action sur une donnée spécifique")
                c.execute('SELECT id, patient, date FROM collectes WHERE user_email=?', (u_email,))
                items = c.fetchall()
                if items:
                    options = {f"ID: {item[0]} | {item[1]} ({item[2]})": item[0] for item in items}
                    selection = st.selectbox("Sélectionnez la donnée à gérer", list(options.keys()))
                    selected_id = options[selection]

                    col_edit, col_del = st.columns(2)
                    
                    with col_edit:
                        st.write("🔧 **Modifier**")
                        new_name = st.text_input("Nouveau nom du patient")
                        if st.button("Mettre à jour le nom"):
                            c.execute('UPDATE collectes SET patient=? WHERE id=?', (new_name, selected_id))
                            conn.commit()
                            st.success("Nom modifié !")
                            st.rerun()

                    with col_del:
                        st.write("⚠️ **Zone de danger**")
                        if st.button("🗑️ Supprimer définitivement"):
                            c.execute('DELETE FROM collectes WHERE id=?', (selected_id,))
                            conn.commit()
                            st.warning("Donnée supprimée.")
                            st.rerun()
                else:
                    st.info("Rien à modifier.")

if __name__ == '__main__':
    main()