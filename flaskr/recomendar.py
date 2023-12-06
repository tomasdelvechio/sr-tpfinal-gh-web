import sqlite3
import pandas as pd
import sys
import os

from flask import current_app

import lightfm as lfm
from lightfm import data
from lightfm import cross_validation
from lightfm import evaluation
import surprise as sp

import whoosh as wh
from whoosh import fields
from whoosh import index
from whoosh import qparser

THIS_FOLDER = os.path.dirname(os.path.abspath("__file__"))

def sql_execute(query, params=None):
    con = sqlite3.connect(os.path.join(THIS_FOLDER, "data/data.db"))
    cur = con.cursor()    
    if params:
        res = cur.execute(query, params)
    else:
        res = cur.execute(query)
    
    con.commit()
    con.close()
    return

def sql_select(query, params=None):
    con = sqlite3.connect(os.path.join(THIS_FOLDER, "data/data.db"))
    con.row_factory = sqlite3.Row # esto es para que devuelva registros en el fetchall
    if current_app.config["DEBUG_SQL"]:
        con.set_trace_callback(print)
    cur = con.cursor()
    if params:
        res = cur.execute(query, params)
    else:
        res = cur.execute(query)
    
    ret = res.fetchall()
    con.close()

    return ret

def crear_usuario(id_usuario):
    query = "INSERT INTO users (id) VALUES (?) ON CONFLICT DO NOTHING;" # si el id_usuario existia, se produce un conflicto y le digo que no haga nada
    sql_execute(query, (id_usuario,))
    return

def insertar_interacciones(id_repo, id_usuario, like, interacciones="interactions"):
    query = f"INSERT INTO {interacciones}(repository, user, date, like) VALUES (?, ?, DATETIME('now','localtime'), ?) ON CONFLICT (repository, user) DO UPDATE SET date=DATETIME('now','localtime'), like=?;" # si el date existia lo actualizo
    sql_execute(query, (id_repo, id_usuario, like, like))
    return

def reset_usuario(id_lector, interacciones="interactions"):
    query = f"DELETE FROM {interacciones} WHERE id_lector = ?;"
    sql_execute(query, (id_lector,))
    return

def obtener_libro(id_libro):
    query = "SELECT * FROM libros WHERE id_libro = ?;"
    libro = sql_select(query, (id_libro,))[0]
    return libro

def valorados(user, interacciones="interactions"):
    query = f"SELECT * FROM {interacciones} WHERE user = ? AND like = 1"
    valorados = sql_select(query, (user,))
    return valorados

def ignorados(user, interacciones="interactions"):
    query = f"SELECT * FROM {interacciones} WHERE user = ? AND like = 0"
    ignorados = sql_select(query, (user,))
    return ignorados

def datos_repositories(id_repos):
    query = f"SELECT DISTINCT * FROM repositories WHERE id IN ({','.join(['?']*len(id_repos))})"
    repositories = sql_select(query, id_repos)
    return repositories

def recomendar_top_n(user, n=6, interacciones="interactions"):
    """
    Recomendador orientado a usuarios de los que no se dispone ninguna información
    
    Arma un top de repos:
        - Mas votados positivamente
        - Que el usuario en cuestión no haya valorado ya
        - Si tienen misma cantidad de ratings, ordena por fecha de valoración mas reciente
    """
    
    query = f"""
        SELECT repository, count(*) AS cant, date
          FROM {interacciones}
         WHERE repository NOT IN (SELECT repository FROM {interacciones} WHERE user = ?)
            AND like = 1
         GROUP BY 1
         ORDER BY 2 DESC, 3 DESC
         LIMIT {n}
    """
    repositories = [r["repository"] for r in sql_select(query, (user,))]
    return repositories

def recomendar_perfil(id_lector, interacciones="interactions", items="repositories", users="users"):
    # TODO: usar otras columnas además de genlit
    # TODO: usar datos del usuario para el perfil
    # TODO: usar cantidad de interacciones para desempatar los scores de perfil iguales
    # TODO: usar los items ignorados

    con = sqlite3.connect(os.path.join(THIS_FOLDER, "data/data.db"))
    df_int = pd.read_sql_query(f"SELECT * FROM {interacciones}", con)
    df_items = pd.read_sql_query(f"SELECT * FROM {items}", con)
    df_users = pd.read_sql_query(f"SELECT * FROM {users}", con)
    con.close()

    df_items["genero"] = df_items["genero"].replace({
        "Autoayuda": "Autoayuda Y Espiritualidad", 
        "Biografías": "Biografías, Memorias", 
        "Clasicos de la literatura": "Clásicos de la literatura",
        "Cómics": "Cómics, Novela Gráfica",
        "Ensayo": "Estudios y ensayos",
        "Juvenil": "Infantil y juvenil",
        "No Ficción": "No ficción",
        "Novela negra": "Novela negra, intriga, terror",
        "Poesía": "Poesía, teatro",
        "Policiaca. Novela negra en bolsillo": "Novela negra, intriga, terror",
        "Histórica en bolsillo": "Narrativa histórica",
        })
    df_items = df_items.rename(columns={"genero": "genlit"}) # para que no coincida con el campos de los usuarios
    
    perf_items = pd.get_dummies(df_items[["id_libro", "genlit"]], columns=["genlit"]).set_index("id_libro")

    perf_usuario = df_int[(df_int["id_lector"] == id_lector) & (df_int["rating"] > 0)].merge(perf_items, on="id_libro")

    for c in perf_usuario.columns:
        if c.startswith("genlit_"):
            perf_usuario[c] = perf_usuario[c] * perf_usuario["rating"]

    perf_usuario = perf_usuario.drop(columns=["id_libro", "rating"]).groupby("id_lector").mean()
    perf_usuario = perf_usuario / perf_usuario.sum(axis=1)[0] # normalizo
    for g in perf_items.columns:
        perf_items[g] = perf_items[g] * perf_usuario[g][0]

    libros_leidos_o_vistos = df_int.loc[df_int["id_lector"] == id_lector, "id_libro"].tolist()
    recomendaciones = [l for l in perf_items.sum(axis=1).sort_values(ascending=False).index if l not in libros_leidos_o_vistos][:9]
    return recomendaciones

def recomendar_lightfm(id_lector, interacciones="interactions"):
    # TODO: optimizar hiperparámetros
    # TODO: entrenar el modelo de forma parcial
    # TODO: user item_features y user_features
    # TODO: usar los items ignorados (usar pesos)

    con = sqlite3.connect(os.path.join(THIS_FOLDER, "data/data.db"))
    df_int = pd.read_sql_query(f"SELECT * FROM {interacciones} WHERE rating > 0", con)
    df_items = pd.read_sql_query("SELECT * FROM libros", con)
    con.close()

    ds = lfm.data.Dataset()
    ds.fit(users=df_int["id_lector"].unique(), items=df_items["id_libro"].unique())
    
    user_id_map, user_feature_map, item_id_map, item_feature_map = ds.mapping()
    (interactions, weights) = ds.build_interactions(df_int[["id_lector", "id_libro", "rating"]].itertuples(index=False))

    model = lfm.LightFM(no_components=20, k=5, n=10, learning_schedule='adagrad', loss='logistic', learning_rate=0.05, rho=0.95, epsilon=1e-06, item_alpha=0.0, user_alpha=0.0, max_sampled=10, random_state=42)
    model.fit(interactions, sample_weight=weights, epochs=10)

    libros_leidos = df_int.loc[df_int["id_lector"] == id_lector, "id_libro"].tolist()
    todos_los_libros = df_items["id_libro"].tolist()
    libros_no_leidos = set(todos_los_libros).difference(libros_leidos)
    predicciones = model.predict(user_id_map[id_lector], [item_id_map[l] for l in libros_no_leidos])

    recomendaciones = sorted([(p, l) for (p, l) in zip(predicciones, libros_no_leidos)], reverse=True)[:9]
    recomendaciones = [libro[1] for libro in recomendaciones]
    return recomendaciones

def recomendar_surprise(id_lector, interacciones="interactions"):
    con = sqlite3.connect(os.path.join(THIS_FOLDER, "data/data.db"))
    df_int = pd.read_sql_query(f"SELECT * FROM {interacciones}", con)
    df_items = pd.read_sql_query("SELECT * FROM libros", con)
    con.close()
    
    reader = sp.reader.Reader(rating_scale=(1, 10))

    data = sp.dataset.Dataset.load_from_df(df_int.loc[df_int["rating"] > 0, ['id_lector', 'id_libro', 'rating']], reader)
    trainset = data.build_full_trainset()
    model = sp.prediction_algorithms.matrix_factorization.SVD(n_factors=500, n_epochs=20, random_state=42)
    model.fit(trainset)

    libros_leidos_o_vistos = df_int.loc[df_int["id_lector"] == id_lector, "id_libro"].tolist()
    todos_los_libros = df_items["id_libro"].tolist()
    libros_no_leidos_ni_vistos = set(todos_los_libros).difference(libros_leidos_o_vistos)
    
    predicciones = [model.predict(id_lector, l).est for l in libros_no_leidos_ni_vistos]
    recomendaciones = sorted([(p, l) for (p, l) in zip(predicciones, libros_no_leidos_ni_vistos)], reverse=True)[:9]

    recomendaciones = [libro[1] for libro in recomendaciones]
    return recomendaciones

def recomendar_whoosh(id_lector, interacciones="interactions"):
    con = sqlite3.connect(os.path.join(THIS_FOLDER, "data/data.db"))
    df_int = pd.read_sql_query(f"SELECT * FROM {interacciones}", con)
    df_items = pd.read_sql_query("SELECT * FROM libros", con)
    con.close()

    # TODO: usar cant
    terminos = []    
    for campo in ["editorial", "autor", "genero"]:
        query = f"""
            SELECT {campo} AS valor, count(*) AS cant
            FROM {interacciones} AS i JOIN libros AS l ON i.id_libro = l.id_libro
            WHERE id_lector = ?
            AND rating > 0
            GROUP BY {campo}
            HAVING cant > 1
            ORDER BY cant DESC
            LIMIT 3
        """       
        rows = sql_select(query, (id_lector,))

        for row in rows:
            terminos.append(wh.query.Term(campo, row["valor"]))
    
    query = wh.query.Or(terminos)

    libros_leidos_o_vistos = df_int.loc[df_int["id_lector"] == id_lector, "id_libro"].tolist()

    # TODO: usar el scoring
    # TODO: ampliar la busqueda con autores parecidos (matriz de similitudes de autores)
    ix = wh.index.open_dir("indexdir")
    with ix.searcher() as searcher:
        results = searcher.search(query, terms=True, scored=True, limit=1000)
        recomendaciones = [r["id_libro"] for r in results if r not in libros_leidos_o_vistos][:9]

    return recomendaciones

def recomendar(id_usuario, interacciones="interactions"):
    # TODO: combinar mejor los recomendadores
    # TODO: crear usuarios fans para llenar la matriz

    cant_valorados = len(valorados(id_usuario, interacciones))
    if cant_valorados <= current_app.config["UMBRAL_TOP_N"] or current_app.config["DEBUG_TOP"]:
        print("recomendador: topN", file=sys.stdout)
        id_repos = recomendar_top_n(id_usuario, interacciones=interacciones)
    elif cant_valorados <= current_app.config["UMBRAL_PERFIL"] or current_app.config["DEBUG_PERFIL"]:
        print("recomendador: perfil", file=sys.stdout)
        id_repos = recomendar_perfil(id_usuario, interacciones)
    else:
        print("recomendador: surprise", file=sys.stdout)
        #id_repos = recomendar_surprise(id_usuario, interacciones)
        #id_repos = recomendar_lightfm(id_usuario, interacciones)
        id_repos = recomendar_whoosh(id_usuario, interacciones)


    # TODO: como completo las recomendaciones cuando vienen menos de 9?

    recomendaciones = datos_repositories(id_repos)

    return recomendaciones

