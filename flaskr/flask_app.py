from __init__ import create_app
from flask import Flask, request, render_template, make_response, redirect, send_from_directory, jsonify
import recomendar
import os
from db import get_top_users

app = create_app()


@app.route('/', methods=('GET', 'POST'))
def login():
    # si me mandaron el formulario y tiene id_usuario...
    if request.method == 'POST' and 'id_usuario' in request.form:
        id_usuario = request.form['id_usuario']

        # creo el usuario al insertar el id_usuario en la tabla "lectores"
        recomendar.crear_usuario(id_usuario)

        # mando al usuario a la página de recomendaciones
        res = make_response(redirect("/recomendaciones"))

        # pongo el id_usuario en una cookie para recordarlo
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

    # me envían el formulario
    #if request.method == 'POST':
    #    for id_repo in request.form.keys():
    #        rating = int(request.form[id_repo])
    #        recomendar.insertar_interacciones(id_repo, id_usuario, rating)

    # recomendaciones
    repos = recomendar.recomendar(id_usuario)

    # pongo repos vistos con rating = 0
    #for repo in repos:
    #    recomendar.insertar_interacciones(repo["id"], id_usuario, False)

    cant_valorados = len(recomendar.valorados(id_usuario))
    cant_ignorados = len(recomendar.ignorados(id_usuario))

    return render_template(
        "recomendaciones.html",
        repos=repos,
        id_usuario=id_usuario,
        cant_valorados=cant_valorados,
        cant_ignorados=cant_ignorados,
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
        own_profile = True
        print("es mi profile")
    else:
        own_profile = False
        print("es el profile de otro")
    liked_repos = recomendar.valorados(username)
    repositories = [r["repository"] for r in liked_repos]
    repos = recomendar.datos_repositories(repositories)
    return render_template(
        "profile.html",
        repos=repos,
        id_usuario=id_usuario,
        username=username,
        cant_valorados=100,
        cant_ignorados=100,
        own_profile=own_profile,
        title="Profile")

if __name__ == "__main__":
    app.run(debug=True)
