import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import psycopg2


def get_connection():
    try:
        conn = psycopg2.connect(
            dbname="consommation_elec",
            user="....",
            password="....",
            host="localhost",
            port="5432"
        )

    except psycopg2.OperationalError as error:
        print(f"OperationalError: {error}")

    return conn
    
def get_filter(conn):

    filters = {
        "type_filiere": pd.read_sql_query("SELECT DISTINCT type_filiere FROM filiere ORDER BY type_filiere;", con=conn)["type_filiere"].to_list(),
        "annee": pd.read_sql_query("SELECT DISTINCT annee FROM temps ORDER BY annee;", con=conn)["annee"].to_list(),
        "type_secteur": pd.read_sql_query("SELECT DISTINCT type_secteur FROM secteur ORDER BY type_secteur;", con=conn)["type_secteur"].to_list(),
        "nom_departement": pd.read_sql_query("SELECT DISTINCT nom_departement FROM departement ORDER BY nom_departement;", con=conn)["nom_departement"].to_list(),
        "nom_region": pd.read_sql_query("SELECT DISTINCT nom_region FROM region ORDER BY nom_region;", con=conn)["nom_region"].to_list(),
        "categorie_consommation": pd.read_sql_query("SELECT DISTINCT categorie_consommation FROM consommation ORDER BY categorie_consommation;", con=conn)["categorie_consommation"].to_list(),
        "operateur": pd.read_sql_query("SELECT DISTINCT operateur FROM consommation ORDER BY operateur;", con=conn)["operateur"].to_list()
    }
    return filters
    

def get_data(conn):
    query = """
        SELECT consommation.*, filiere.type_filiere, temps.annee, secteur.type_secteur, 
       departement.nom_departement, region.nom_region
        FROM consommation
        JOIN filiere ON consommation.filiere_id = filiere.filiere_id
        JOIN temps ON consommation.temps_id = temps.temps_id
        JOIN secteur ON consommation.secteur_id = secteur.secteur_id
        JOIN departement ON consommation.departement_id = departement.departement_id
        JOIN region ON consommation.region_id = region.region_id;

    """
    try:
        df = pd.read_sql_query(query, con=conn)

        num_cols = ["conso_totale", "conso_moyenne", "nb_sites"]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    except Exception as e:
        print(f"Erreur SQL : {e}")
        return None

st.title("Bienvenue sur mon Tableau de Bord Énergétique")

conn = get_connection()
if conn:
    df = get_data(conn)
    filters = get_filter(conn)
    
    tab1, tab2 = st.tabs(["Exploration de la BDD", "Tableau de Bord"])

    with tab1:
        st.header("Exploration des données énergétiques")
        st.write(df.head())  # Aperçu des données
        st.markdown(f"**Dimensions du DataFrame :** {df.shape}")
        st.write("**Colonnes disponibles :**", df.columns)

        categorical_cols = df.select_dtypes(include="object").columns.to_list()
        st.subheader("Variables qualitatives")
        st.write(categorical_cols)

        numerical_cols = df.select_dtypes(exclude="object").columns.to_list()
        st.subheader("Variables quantitatives")
        st.write(numerical_cols)

    with tab2:
        # Sélection de filtres
        var_quali = st.selectbox("Choisissez une variable catégorielle à analyser", categorical_cols)
        filtre = st.radio("Voulez-vous ajouter un filtre ?", ["Non", "Oui"])
        
        df_filtered = df

        if filtre == "Oui":
            var_filtre = st.selectbox("Choisissez une variable de filtre", list(filters.keys()))
            modalites = ["Toutes"] + filters[var_filtre]
            modalite_choisie = st.selectbox(f"Choisissez une modalité de '{var_filtre}'", modalites)

            if modalite_choisie != "Toutes":
                df_filtered = df[df[var_filtre] == modalite_choisie]

        df_quali = df_filtered[var_quali].value_counts().reset_index()
        df_quali.columns = [var_quali, "count"]

        # 📊 Visualisation des données qualitatives
        if len(df_quali) > 10:
            fig_quali = px.bar(df_quali.sort_values("count", ascending=False).head(10),
                               x=var_quali, y="count",
                               title=f"Top 10 des modalités de {var_quali}")
        else:
            fig_quali = px.pie(df_quali, names=var_quali, values="count",
                               title=f"Répartition des modalités de {var_quali}")

        st.plotly_chart(fig_quali)

        # 📈 Visualisation des données quantitatives
        var_x = st.selectbox("Choisissez la variable en abscisse", list(filters.keys()))
        var_y = st.selectbox("Choisissez la variable en ordonnée", ["conso_totale", "conso_moyenne", "Nb_sites"])

        def repartition(var_x, var_y):
            df_grouped = df.groupby(var_x)[var_y].sum().reset_index()
            nb_modalite = df_grouped[var_x].nunique()

            if nb_modalite <= 6:
                fig = px.pie(df_grouped, names=var_x, values=var_y,
                             title=f"Répartition de {var_y} selon {var_x}")
            elif 6 <= nb_modalite <= 15:
                fig = px.bar(df_grouped, x=var_x, y=var_y, title=f"{var_y} par {var_x}",
                             labels={var_x: var_x, var_y: var_y}, text_auto=True, color=var_y)
            else:
                fig = px.line(df_grouped, x=var_x, y=var_y,
                              title=f"{var_y} par {var_x}",
                              labels={var_x: var_x, var_y: var_y})

            st.plotly_chart(fig)

        repartition(var_x, var_y)

else:
    st.error("Impossible de se connecter à la base de données PostgreSQL")
