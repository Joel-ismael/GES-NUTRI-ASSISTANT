import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import plotly.express as px
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Nutri-Soutien Pro", page_icon="🥗", layout="wide")

# CSS POUR FORCER LA VISIBILITÉ DU MENU SUR MOBILE
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;} 
    header {visibility: hidden;}
    
    /* Style pour le bouton de la sidebar sur mobile */
    .st-emotion-cache-15dx93d {
        background-color: #2ecc71 !important;
        color: white !important;
        border-radius: 50%;
    }
    
    /* Rendre les onglets défilables sur mobile si nécessaire */
    div.stTabs button {
        font-size: 14px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- BASE DE DONNÉES ---
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

# --- LOGIQUE DE CALCUL DU STATUT ---
def calculer_statut(imc):
    if imc < 18.5:
        return "Insuffisance pondérale"
    elif 18.5 <= imc < 25:
        return "Poids normal"
    elif 25 <= imc < 30:
        return "Surpoids"
    else:
        return "Obésité"

def hash_pwd(pwd):
    return hashlib.sha256(str.encode(pwd)).hexdigest()

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_info = None

def main():
    if not st.session_state.authenticated:
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
                    except: st.error("Erreur : Email déjà utilisé.")
        else:
            with st.form("login"):
                l_n, l_p, l_pw = st.text_input("Nom"), st.text_input("Prénom"), st.text_input("Mot de passe", type='password')
                if st.form_submit_button("Connexion"):
                    c.execute('SELECT * FROM users WHERE nom=? AND prenom=? AND password=?', (l_n, l_p, hash_pwd(l_pw)))
                    user = c.fetchone()
                    if user:
                        st.session_state.authenticated, st.session_state.user_info = True, list(user)
                        st.rerun()
                    else: st.error("Identifiants incorrects.")

    else:
        u_email = st.session_state.user_info[0]
        # PARTIE NAVIGATION
        st.sidebar.title(f"👤 {st.session_state.user_info[2]}")
        menu = st.sidebar.selectbox("Navigation", ["Collecte & Gestion", "Mon Compte", "Déconnexion"])

        if menu == "Déconnexion":
            st.session_state.authenticated = False
            st.rerun()

        elif menu == "Mon Compte":
            st.header("⚙️ Paramètres du compte")
            st.info(f"Email du compte : {u_email}")
            
            with st.form("edit_account"):
                new_nom = st.text_input("Nom", value=st.session_state.user_info[1])
                new_prenom = st.text_input("Prénom", value=st.session_state.user_info[2])
                new_pw = st.text_input("Nouveau mot de passe (laisser vide pour ne pas changer)", type='password')
                
                if st.form_submit_button("Enregistrer les modifications"):
                    if new_pw:
                        hashed_new_pw = hash_pwd(new_pw)
                        c.execute('UPDATE users SET nom=?, prenom=?, password=? WHERE email=?', (new_nom, new_prenom, hashed_new_pw, u_email))
                    else:
                        c.execute('UPDATE users SET nom=?, prenom=? WHERE email=?', (new_nom, new_prenom, u_email))
                    
                    conn.commit()
                    st.session_state.user_info[1] = new_nom
                    st.session_state.user_info[2] = new_prenom
                    st.success("Informations mises à jour !")
                    st.rerun()

        elif menu == "Collecte & Gestion":
            st.header("📋 Gestion des données patients")
            tab_saisie, tab_histo, tab_modif = st.tabs(["📥 Saisie", "📊 Archives & Graphique", "🛠️ Modifier/Supprimer"])
            
            with tab_saisie:
                with st.form("form_saisie"):
                    p_nom = st.text_input("Nom du Patient")
                    poids = st.number_input("Poids (kg)", 1.0, 250.0, 70.0)
                    taille = st.number_input("Taille (cm)", 50, 250, 170)
                    if st.form_submit_button("Sauvegarder"):
                        imc = round(poids / ((taille/100)**2), 2)
                        statut = calculer_statut(imc)
                        c.execute('INSERT INTO collectes (user_email, date, patient, poids, taille, imc, statut) VALUES (?,?,?,?,?,?,?)',
                                 (u_email, datetime.now().strftime("%d/%m/%Y"), p_nom, poids, taille, imc, statut))
                        conn.commit()
                        st.success(f"Enregistré : {p_nom} est en '{statut}' (IMC: {imc})")

            with tab_histo:
                c.execute('SELECT date, patient, imc, statut FROM collectes WHERE user_email=?', (u_email,))
                rows = c.fetchall()
                if rows:
                    df = pd.DataFrame(rows, columns=["Date", "Patient", "IMC", "Statut"])
                    col_t, col_g = st.columns(2)
                    with col_t: st.dataframe(df, use_container_width=True)
                    with col_g:
                        fig = px.pie(df, names='Statut', hole=0.4, color='Statut',
                                     color_discrete_map={
                                         'Poids normal':'#2ecc71', 
                                         'Insuffisance pondérale':'#3498db', 
                                         'Surpoids':'#f1c40f', 
                                         'Obésité':'#e74c3c'
                                     })
                        st.plotly_chart(fig, use_container_width=True)
                else: st.info("Aucune donnée.")

            with tab_modif:
                c.execute('SELECT id, patient, poids, taille FROM collectes WHERE user_email=?', (u_email,))
                items = c.fetchall()
                if items:
                    options = {f"ID: {item[0]} | {item[1]}": item[0] for item in items}
                    selection = st.selectbox("Sélectionnez le patient à modifier", list(options.keys()))
                    selected_id = options[selection]
                    
                    c.execute('SELECT patient, poids, taille FROM collectes WHERE id=?', (selected_id,))
                    current_data = c.fetchone()

                    with st.form("edit_full"):
                        st.write("🔧 **Modification complète**")
                        edit_name = st.text_input("Nom du patient", value=current_data[0])
                        edit_poids = st.number_input("Poids (kg)", value=current_data[1])
                        edit_taille = st.number_input("Taille (cm)", value=current_data[2])
                        
                        if st.form_submit_button("Appliquer les modifications"):
                            new_imc = round(edit_poids / ((edit_taille/100)**2), 2)
                            new_statut = calculer_statut(new_imc)
                            c.execute('''UPDATE collectes SET patient=?, poids=?, taille=?, imc=?, statut=? 
                                         WHERE id=?''', (edit_name, edit_poids, edit_taille, new_imc, new_statut, selected_id))
                            conn.commit()
                            st.success("Fiche mise à jour !")
                            st.rerun()

                    if st.button("🗑️ Supprimer définitivement"):
                        c.execute('DELETE FROM collectes WHERE id=?', (selected_id,))
                        conn.commit()
                        st.warning("Donnée supprimée.")
                        st.rerun()
                else:
                    st.info("Rien à modifier.")

if __name__ == '__main__':
    main()