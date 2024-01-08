from __init__ import create_app
from flask import request, render_template, make_response, redirect, send_from_directory, jsonify
import recomendar
import os
from db import get_top_users

app = create_app()


@app.route('/', methods=('GET', 'POST'))
def login():
    # si me mandaron el formulario y tiene id_usuario...
    if request.method == 'POST' and 'id_usuario' in request.form:
        id_usuario = request.form['id_usuario']
        recomendar.crear_usuario(id_usuario)
        res = make_response(redirect("/recomendaciones"))
        res.set_cookie('id_usuario', id_usuario)
        return res

    # si alguien entra a la página principal y conozco el usuario
    if request.method == 'GET' and 'id_usuario' in request.cookies:
        return make_response(redirect("/recomendaciones"))

    # sino, le muestro el formulario de login
    top_n = get_top_users()  # muestro sugerencia de usuarios para probar
    return render_template('login.html', top_n=top_n)


@app.route('/recomendaciones', methods=('GET', 'POST'))
def recomendaciones():
    id_usuario = request.cookies.get('id_usuario')

    # recomendaciones
    repos, recomendador_activo = recomendar.recomendar(id_usuario)

    cant_valorados = recomendar.get_own_repos()

    return render_template(
        "recomendaciones.html",
        repos=repos,
        id_usuario=id_usuario,
        cant_valorados=len(cant_valorados),
        recomendador_activo=recomendador_activo,
        title="Recomendaciones")


@app.route('/reset')
def reset():
    id_usuario = request.cookies.get('id_usuario')
    recomendar.reset_usuario(id_usuario)

    return make_response(redirect("/recomendaciones"))


@app.route('/static/favicon.ico')
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon')


@app.route('/like', methods=['POST'])
def like():
    like_interaction = request.json
    id_usuario = request.cookies.get('id_usuario')
    # example:
    #   {'id': 'pytorch/pytorch', 'like': False}
    try:
        if like_interaction['like']:
            recomendar.insertar_interacciones(like_interaction["id"], id_usuario)
        else:
            recomendar.eliminar_interaccion(like_interaction["id"], id_usuario)
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(e.message)
        return jsonify({"status": "error"}), 500


@app.route('/profile/<username>')
def profile(username):
    id_usuario = request.cookies.get('id_usuario')
    if (id_usuario == username):
        title = "Tu perfil"
    else:
        title = f"Perfil de { username }"
    liked_repos = recomendar.valorados(username)
    own_repos = recomendar.get_own_repos()
    repositories = [r["repository"] for r in liked_repos]
    repos = recomendar.datos_repositories(repositories)
    return render_template(
        "profile.html",
        repos=repos,
        id_usuario=id_usuario,
        username=username,
        cant_valorados=len(own_repos),
        own_repos=own_repos,
        title=title)


@app.route('/users')
def users():
    id_usuario = request.cookies.get('id_usuario')
    usuarios = recomendar.get_users()
    cant_valorados = recomendar.get_own_repos()
    return render_template(
        "usuarios.html",
        usuarios=usuarios,
        id_usuario=id_usuario,
        cant_valorados=len(cant_valorados),
        title="Buscar usuarios"
    )


@app.route('/close')
def close():
    res = make_response(redirect("/"))
    res.set_cookie('id_usuario', '', expires=0)
    return res


if __name__ == "__main__":
    app.run(debug=True)
