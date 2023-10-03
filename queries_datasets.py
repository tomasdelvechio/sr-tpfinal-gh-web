# %matplotlib tk
import sqlite3
import pandas as pd

con = sqlite3.connect("data/data.db")
df_repos = pd.read_sql_query("SELECT * FROM repositories", con)
con.close()

# df_repos.hist() # muestra el histograma de las columnas
len_df = df_repos.shape[0]
print(f"index: {len(df_repos.index.value_counts())/len_df}")
print(f"id: {len(df_repos.id.value_counts())/len_df}")
print(f"es_fork: {len(df_repos.es_fork.value_counts())/len_df}")
print(f"forks: {len(df_repos.forks.value_counts())/len_df}")
print(f"stars: {len(df_repos.stars.value_counts())/len_df}")
print(f"watchers: {len(df_repos.watchers.value_counts())/len_df}")
print(f"issues: {len(df_repos.issues.value_counts())/len_df}")
print(f"about: {len(df_repos.about.value_counts())/len_df}")
print(f"subscribers: {len(df_repos.subscribers.value_counts())/len_df}")
print(f"archived: {len(df_repos.archived.value_counts())/len_df}")
print(f"topics: {len(df_repos.topics.value_counts())/len_df}")
print(f"language: {len(df_repos.language.value_counts())/len_df}")

