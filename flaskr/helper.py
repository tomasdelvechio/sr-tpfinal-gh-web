import sys
import os

def dd(something):
    print(f"{something}")
    sys.exit(1)

def fullpath(filepath, app=None):
    project_path = app.root_path
    return os.path.join(project_path, '..', filepath)