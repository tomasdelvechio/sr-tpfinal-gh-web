class BaseRecommender:
    """
        Abstract class for define a recommender to be use in the
        recomendation process. Set a uniform set of methods for all
        recommenders.
        
        Methods to be implemented:
         - load_data()
         - setup_model()
    """
    
    def load_data(self):
        """A way to load the data for train or setup the recommender
        """
        raise NotImplementedError("You must implement this")

    def setup_model(self):
        """Load or fit a valid recommendation model
        """
        raise NotImplementedError("You must implement this")
    
    def recommend_by_user(self, username):
        """Make a recommendation based on data of an user
        """
        raise NotImplementedError("You must implement this")