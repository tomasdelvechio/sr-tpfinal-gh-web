import sqlite3
import pandas as pd
import sys
import os

from flask import current_app, request

from recommenders.ImplicitRecommender import ImplicitRecommender

THIS_FOLDER = os.path.dirname(os.path.abspath("__file__"))

def sql_execute(query, params=None):
    con = sqlite3.connect(os.path.join(THIS_FOLDER, "data/data.db"))
    if current_app.config["DEBUG_SQL"]:
        con.set_trace_callback(print)
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

def insertar_interacciones(id_repo, id_usuario, interacciones="interactions"):
    query = f"INSERT INTO {interacciones}(repository, user, date) VALUES (?, ?, DATETIME('now','localtime')) ON CONFLICT (repository, user) DO UPDATE SET date=DATETIME('now','localtime');" # si el date existia lo actualizo
    sql_execute(query, (id_repo, id_usuario))
    return

def eliminar_interaccion(id_repo, id_usuario, interacciones="interactions"):
    query = f"DELETE FROM {interacciones} WHERE user = ? AND repository = ?;"
    sql_execute(query, (id_usuario, id_repo))
    return

def reset_usuario(id_usuario, interacciones="interactions"):
    query = f"DELETE FROM {interacciones} WHERE user = ?;"
    sql_execute(query, (id_usuario,))
    return


def valorados(user, interacciones="interactions"):
    query = f"SELECT * FROM {interacciones} WHERE user = ?"
    valorados = sql_select(query, (user,))
    return valorados

def get_own_repos():
    id_usuario = request.cookies.get('id_usuario')
    liked_repos = valorados(id_usuario)
    return [r["repository"] for r in liked_repos]

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
         GROUP BY 1
         ORDER BY 2 DESC, 3 DESC
         LIMIT {n}
    """
    repositories = [r["repository"] for r in sql_select(query, (user,))]
    return repositories


def recomendar_perfil(username, n=6, interacciones="interactions", items="repositories", users="users"):
    """
    Recomendador basado en el contenido
    """

    con = sqlite3.connect(os.path.join(THIS_FOLDER, "data/data.db"))
    df_int = pd.read_sql_query(f"SELECT * FROM {interacciones}", con)
    original_df_items = pd.read_sql_query(f"SELECT * FROM {items}", con)
    df_items = original_df_items.drop(["es_fork", "about", "archived", "topics", "language"], axis=1)
    con.close()
    
    # dummy de lenguajes y topics
    df_languaje_dummies = original_df_items.language.str.get_dummies(sep=";")
    df_topics_dummies = original_df_items.topics.str.get_dummies(sep=";")
    df_perfil_items = pd.concat([df_items, df_languaje_dummies, df_topics_dummies], axis=1)

    repos_user = df_int.loc[
        (df_int["user"] == username),
        "repository"].to_list()

    # me quedo con el perfil del usuario de los repos que le gustaron
    perfil_user = df_perfil_items[df_perfil_items["id"].isin(repos_user)].drop(columns=["id", "stars", "watchers", "forks", "issues", "subscribers"]).sum(axis=0).sort_values(ascending=False)
    perfil_user = perfil_user / perfil_user.sum() # normalizo

    df_perfil_user = df_perfil_items.drop(columns=["stars", "watchers", "forks", "issues", "subscribers"]).set_index("id").copy()

    # por ahora dimension son lenguajes, pero podria haber topics
    for dimension in df_perfil_user.columns:
        df_perfil_user[dimension] = df_perfil_user[dimension] * perfil_user[dimension]

    # filtrar repos con los que ya interactuó
    df_perfil_user = df_perfil_user.drop(repos_user)

    rank = df_perfil_user.sum(axis=1).sort_values(ascending=False)[:n]
    df_recomendacion_scores = pd.DataFrame({'repository': rank.index, 'score': rank.values})
    df_recomendacion_scores

    df_recomendacion_fechas = (df_int[df_int["repository"].isin(list(df_recomendacion_scores.repository))].sort_values('date').groupby('repository').tail(1))[["repository", "date"]]
    df_recomendacion_fechas

    df_recomendacion = pd.merge(df_recomendacion_fechas, df_recomendacion_scores, on="repository")#.sort_values(['score', 'date'], ascending=[False, False])
    df_recomendacion["date"] = pd.to_datetime(df_recomendacion["date"])
    df_recomendacion = df_recomendacion.sort_values(['score', 'date'], ascending=[False, False]).reset_index(drop=True)

    recomendaciones = list(df_recomendacion.reset_index(drop=True).repository)
    return recomendaciones


def built_implicit_engine():
    recomendador = ImplicitRecommender()
    recomendador.load_data()
    recomendador.setup_model()
    return recomendador

def recomendar_implicit(username):
    recomendador = built_implicit_engine()
    recommendations = recomendador.recommend_by_user(username, N=9)
    return list(recommendations.repositories)

def recomendar_users_implicit(username, n=100):
    recomendador = built_implicit_engine()
    recommendations = recomendador.recommend_users(username, N=n)
    return list(recommendations.users)

def recomendar(id_usuario, interacciones="interactions"):

    recomendador_activo = {'type': None, 'why': None}
    cant_valorados = len(valorados(id_usuario, interacciones))
    if cant_valorados < current_app.config["UMBRAL_TOP_N"] or current_app.config["DEBUG_TOP"]:
        print("recomendador: topN", file=sys.stdout)
        recomendador_activo["type"] = "Top mas populares"
        recomendador_activo["why"] = f"Porque valoraste menos de {current_app.config['UMBRAL_TOP_N']} repositorios ({cant_valorados})"
        id_repos = recomendar_top_n(id_usuario, n=12, interacciones=interacciones)
    elif cant_valorados <= current_app.config["UMBRAL_PERFIL"] or current_app.config["DEBUG_PERFIL"]:
        print("recomendador: perfil", file=sys.stdout)
        recomendador_activo["type"] = "Filtro básado en contenido"
        recomendador_activo["why"] = f"Porque valoraste mas de {current_app.config['UMBRAL_TOP_N']} pero menos de {current_app.config['UMBRAL_PERFIL']} repositorios ({cant_valorados})"
        id_repos = recomendar_perfil(id_usuario, n=12, interacciones=interacciones)
    else:
        print("recomendador: implicit", file=sys.stdout)
        recomendador_activo["type"] = "Filtro Colaborativo (engine: implicit)"
        recomendador_activo["why"] = f"Porque valoraste mas de {current_app.config['UMBRAL_PERFIL']} repositorios ({cant_valorados})"
        id_repos = recomendar_implicit(id_usuario)

    recomendaciones = datos_repositories(id_repos)

    return recomendaciones, recomendador_activo


def recomendar_usuarios(id_usuario, interacciones="interactions"):
    try:
        similar_users = recomendar_users_implicit(id_usuario, n=20)
        return get_users_by_list(similar_users, list_of_users_out=[id_usuario]), "Usuarios recomendados", f"Usuarios similares a {id_usuario} basado en sus likes"
    except KeyError:
        # El usuario no existe en el modelo, mandamos un top
        return get_users(), "Usuarios recomendados", f"Usuarios populares (en base a sus seguidores)"


def get_users(n=100, where=None):
    where_clause = ""
    if where is not None:
        where_clause = f" WHERE {where} "
    query = f"SELECT DISTINCT id, gh_id, name, bio FROM users {where_clause} ORDER BY followers DESC, following DESC LIMIT ?"
    users = sql_select(query, (n,))
    return users


def get_users_params(n=100, where=None, params=()):
    where_clause = ""
    if where is not None:
        where_clause = f" WHERE {where} "
    query = f"SELECT DISTINCT id, gh_id, name, bio FROM users {where_clause} ORDER BY followers DESC, following DESC LIMIT ?"
    users = sql_select(query, params+(n,))
    return users


def get_users_by_list(list_of_users_in, list_of_users_out=None, n=100):
    params = tuple(list_of_users_in)
    where_users_in = ",".join(['?']*len(list_of_users_in))
    where_users_out = ""
    if list_of_users_out is not None:
        where_users_out = ",".join(['?']*len(list_of_users_out))
        where_users_out = f" AND id NOT IN ({where_users_out}) "
        params = params + tuple(list_of_users_out)
    where_condition = f" id IN ({where_users_in}) {where_users_out} "
    return get_users_params(n=n, where=where_condition, params=params)