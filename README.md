# Sistema de Recomendación - Frontend Web

Sistema Web que implementa un sistema de recomendación basado en el dataset construido
por [este repositorio](https://github.com/tomasdelvechio/sr-tpfinal-gh).

Este sistema implementa 3 tipos de recomendadores:

 * Filtro de popularidad (para nuevos usuarios con ningun o pocos likes)
 * Filtro basado en contenido (para usuarios con una cantidad de likes moderada)
 * Filtro colaborativo via modelos de la [libreria implicit](https://benfred.github.io/implicit/)

Para ver detalles de la elección de implicit y su optimización, referirse a la sección correspondiente en este mismo documento.

# Instalación

Se asume el repositorio clonado en el dispositivo a instalar.

## Generar archivo de configuración

```bash
cp config.py.example config.py
```

[Se recomienda](https://flask.palletsprojects.com/en/2.3.x/config/#SECRET_KEY) generar una `SECRET_KEY`` con el siguiente comando

```bash
python -c 'import secrets; print(secrets.token_hex())'
```

Utilizar el string de salida del comando como valor de `SECRET_KEY` en `config.py`

## Construir entorno

```bash
git clone git@github.com:tomasdelvechio/sr-tpfinal-gh-web.git ~/workspace/sr-tpfinal-gh-web
cd sr-tpfinal-gh-web
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Servidor Web

```bash
python flaskr/flask_app.py
```

# Filtro colaborativo
