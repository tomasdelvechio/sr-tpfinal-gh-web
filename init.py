"""
Script que construye el indice de IR de los items (repositorios)
"""

import sqlite3
import os

import pandas as pd

import whoosh as wh
from whoosh import fields
from whoosh import index
from whoosh import qparser

from helper import dd

THIS_FOLDER = os.path.dirname(os.path.abspath("__file__"))

con = sqlite3.connect(os.path.join(THIS_FOLDER, "data/data.db"))
df_repos = pd.read_sql_query("SELECT * FROM repositories", con)
con.close()
#dd(df_repos.columns)
# imputamos a los  NA
df_repos[["id", "forks", "stars", "watchers", "issues", "about", "subscribers", "archived", "topics", "language",]] = df_repos[["id", "forks", "stars", "watchers", "issues", "about", "subscribers", "archived", "topics", "language",]].fillna(" ")

# TODO: ver field_boost en wh.fields
schema = wh.fields.Schema(
    id=wh.fields.ID(stored=True),
    forks=wh.fields.NUMERIC(),
    stars=wh.fields.NUMERIC(),
    watchers=wh.fields.NUMERIC(),
    issues=wh.fields.NUMERIC(),
    subscribers=wh.fields.NUMERIC(),
    archived=wh.fields.NUMERIC(),
    about=wh.fields.TEXT(),
    topics=wh.fields.KEYWORD(lowercase=True, commas=True),
    language=wh.fields.KEYWORD(lowercase=True, commas=True)
)

ix = wh.index.create_in("indexdir", schema)

writer = ix.writer()
for index, row in df_repos.iterrows():
    writer.add_document(
        id=row["id"],
        forks=row["forks"],
        stars=row["stars"],
        watchers=row["watchers"],
        issues=row["issues"],
        subscribers=row["subscribers"],
        archived=row["archived"],
        about=row["about"],
        topics=row["topics"].replace(';',','),
        language=row["language"].replace(';',',')
    )
writer.commit()
