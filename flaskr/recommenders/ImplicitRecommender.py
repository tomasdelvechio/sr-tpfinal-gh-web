import os
import sqlite3
import numpy as np
import pandas as pd
import threadpoolctl
from scipy.sparse import coo_matrix
from scipy.sparse import csr_matrix

from implicit.als import AlternatingLeastSquares
from implicit.nearest_neighbours import bm25_weight

import db
from recommenders.BaseRecommender import BaseRecommender

class ImplicitRecommender(BaseRecommender):
    """Implements a recommender with Implicit lib like 
        core recommender engine.
    """
    
    def __build_data(self, df):
        try:
            df = df.drop(columns=["index", "date"])
        except:
            pass
        self.usercodes = df.user.astype("category").cat.categories.copy()
        self.repocodes = df.repository.astype("category").cat.categories.copy()
        df = df.dropna().copy()
        users = df.user.astype("category")
        repos = df.repository.astype("category")
        stars = coo_matrix((np.ones(df.shape[0]),
                (repos.cat.codes.copy(),
                users.cat.codes.copy())))
        stars_bm25 = bm25_weight(stars)
        stars_by_users = stars_bm25.T.tocsr()
        return stars_by_users
    
    def __get_usercode(self, username):
        return self.usercodes.get_loc(username)
    
    def load_data(self):
        con = db.get_db()
        df_int = pd.read_sql_query(f"SELECT * FROM interactions", con)
        self.stars = self.__build_data(df_int)
    
    def setup_model(self):
        threadpoolctl.threadpool_limits(1, "blas")
        self.model = AlternatingLeastSquares(
            factors=2,
            regularization=0.18739731219661934,
            iterations=5,
        )
        self.model.fit(self.stars, show_progress=False)
    
    def recommend_by_user(self, username, N=5):
        user_code = self.__get_usercode(username)
        items_ids, items_scores = self.model.recommend(user_code, self.stars[user_code], N=N, filter_already_liked_items=True)
        return pd.DataFrame({"repositories": self.repocodes[items_ids], "scores": items_scores})
    
    def recommend_users(self, username, N=5):
        user_code = self.__get_usercode(username)
        similar_users_ids, similar_users_scores = self.model.similar_users(user_code, N=N)
        return pd.DataFrame({"users": self.usercodes[similar_users_ids], "scores": similar_users_scores})