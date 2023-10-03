# Sistema de Recomendación - Frontend Web

# Uso

# Instalación

## Construir entorno

```bash
git clone git@github.com:tomasdelvechio/sr-tpfinal-gh-web.git ~/workspace/sr-tpfinal-gh-web
cd sr-tpfinal-gh-web
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Inicializar sistema

```bash
python init.py # Crea el indice invertido para busqueda por contenido
```

## Servidor Web

```bash
python flask_app.py
```