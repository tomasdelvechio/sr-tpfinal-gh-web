from flask import Flask, request, render_template, make_response, redirect
import recomendar
import sys

app = Flask(__name__)

@app.route('/', methods=('GET', 'POST'))
def login():
    # si me mandaron el formulario y tiene id_lector... 
    if request.method == 'POST' and 'id_lector' in request.form:
        id_lector = request.form['id_lector']

        # creo el usuario al insertar el id_lector en la tabla "lectores"
        recomendar.crear_usuario(id_lector)

        # mando al usuario a la página de recomendaciones
        res = make_response(redirect("/recomendaciones"))

        # pongo el id_lector en una cookie para recordarlo
        res.set_cookie('id_lector', id_lector)
        return res

    # si alguien entra a la página principal y conozco el usuario
    if request.method == 'GET' and 'id_lector' in request.cookies:
        return make_response(redirect("/recomendaciones"))

    # sino, le muestro el formulario de login
    return render_template('login.html')

@app.route('/recomendaciones', methods=('GET', 'POST'))
def recomendaciones():
    id_lector = request.cookies.get('id_lector')

    # me envían el formulario
    if request.method == 'POST':
        for id_libro in request.form.keys():
            rating = int(request.form[id_libro])
            recomendar.insertar_interacciones(id_libro, id_lector, rating)

    # recomendaciones
    libros = recomendar.recomendar(id_lector)

    # pongo libros vistos con rating = 0
    for libro in libros:
        recomendar.insertar_interacciones(libro["id_libro"], id_lector, 0)

    cant_valorados = len(recomendar.valorados(id_lector))
    cant_ignorados = len(recomendar.ignorados(id_lector))
    
    return render_template("recomendaciones.html", libros=libros, id_lector=id_lector, cant_valorados=cant_valorados, cant_ignorados=cant_ignorados)

@app.route('/reset')
def reset():
    id_lector = request.cookies.get('id_lector')
    recomendar.reset_usuario(id_lector)

    return make_response(redirect("/recomendaciones"))


if __name__ == "__main__":
    app.run(debug=True)