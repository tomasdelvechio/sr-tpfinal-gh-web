from __init__ import create_app
from flask import Flask, request, render_template, make_response, redirect, send_from_directory
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
    top_n = get_top_users() # muestro sugerencia de usuarios para probar
    return render_template('login.html', top_n=top_n)

@app.route('/recomendaciones', methods=('GET', 'POST'))
def recomendaciones():
    id_usuario = request.cookies.get('id_usuario')

    # me envían el formulario
    if request.method == 'POST':
        for id_repo in request.form.keys():
            rating = int(request.form[id_repo])
            recomendar.insertar_interacciones(id_repo, id_usuario, rating)

    # recomendaciones
    repos = recomendar.recomendar(id_usuario)

    # pongo repos vistos con rating = 0
    #for repo in repos:
    #    recomendar.insertar_interacciones(repo["id"], id_usuario, 0)

    cant_valorados = len(recomendar.valorados(id_usuario))
    cant_ignorados = len(recomendar.ignorados(id_usuario))
    
    return render_template("recomendaciones.html", repos=repos, id_usuario=id_usuario, cant_valorados=cant_valorados, cant_ignorados=cant_ignorados, title="Recomendaciones")

@app.route('/reset')
def reset():
    id_usuario = request.cookies.get('id_usuario')
    recomendar.reset_usuario(id_usuario)

    return make_response(redirect("/recomendaciones"))

@app.route('/static/favicon.ico')
def favicon():
    print(app.root_path)
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == "__main__":
    app.run(debug=True)