import os

from flask import Flask, current_app
from helper import fullpath

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=fullpath('data/data.db', app=app)
    )
    
    if test_config is None:
        config_file = fullpath('config.py', app=app)
        app.config.from_pyfile(config_file, silent=True)
    else:
        app.config.from_mapping(test_config)
        
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    @app.route('/testing')
    def testing():
        return "Test route"
    
    import db
    db.init_app(app)

    return app