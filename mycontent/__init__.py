import logging
import os
from readline import append_history_file
import tempfile
#import surprise
from surprise import NormalPredictor
from surprise import Dataset
from surprise import Reader
from surprise.model_selection import cross_validate, train_test_split, GridSearchCV
import azure.functions as func
import pandas as pd
import random
#from io import StringIO
#import pickle
from collections import defaultdict
from urllib.parse import parse_qs
import json
from json import JSONEncoder


def get_top_n(predictions, n=10):
    """Return the top-N recommendation for each user from a set of predictions.
    Args:
        predictions(list of Prediction objects): The list of predictions, as
            returned by the test method of an algorithm.
        n(int): The number of recommendation to output for each user. Default
            is 10.
    Returns:
    A dict where keys are user (raw) ids and values are lists of tuples:
        [(raw item id, rating estimation), ...] of size n.
    """

    # First map the predictions to each user.
    top_n = defaultdict(list)
    for uid, iid, true_r, est, _ in predictions:
        top_n[uid].append((iid, est))

    # Then sort the predictions for each user and retrieve the k highest ones.
    for uid, user_ratings in top_n.items():
        user_ratings.sort(key=lambda x: x[1], reverse=True)
        top_n[uid] = user_ratings[:n]

    return top_n

#Make simple recommendation for user.
def make_recommendation(user_ID, top_n, df, articles_df):
    """Return a list of recommanded articles based on the taste of the user and all recommended categories
    Args:
        user_id -> user id used for recommendation
        top_n -> top-N recommendation for each user from a set of predictions
        df_rating -> df used to train our algo
        articles_df -> df with metadata of all articles.
    Returns:
        list(recommanded articles), list(recommanded categories)
    """
    #Get top 5 cat and adding it to our list
    recommanded_cat = [iid for iid, _ in top_n[user_ID]]
    
    #If we don't have any recommandation, use our data.
    if not recommanded_cat:
        recommanded_cat = df[df['user_id'] == user_ID].nlargest(1, ['rating'])['category_id'].values
   
    #Select 5 randoms articles for each recommanded cat.
    random_articles_by_cat = [articles_df[articles_df['category_id'] == x]['article_id'].sample(5).values for x in recommanded_cat]
    
    #Select one of the recommanded cat and return 5 articles.
    rand_category = random.sample(random_articles_by_cat, 1)

   
    logging.info(f"Python blob trigger function processed blob \n"
                 f"rand_cat: {rand_category}\n")

    return rand_category[0], recommanded_cat

## LOAD SAVED MODEL
def load_model(model_filename):
    print (">> Loading dump")
    from surprise import dump
    import os
    file_name = os.path.expanduser(model_filename)
    _, loaded_model = dump.load(file_name)
    print (">> Loaded dump")
    return loaded_model


def main(req: func.HttpRequest,  inputblob: func.InputStream, inputblob2: func.InputStream, inputblob3: func.InputStream) -> func.HttpResponse:

    logging.info('Python HTTP trigger function processed a request.',)

    tmp_path = tempfile.gettempdir()
    file_model = os.path.join(tmp_path,'model.pickle')
    file_clicks = os.path.join(tmp_path,'clicks_file.csv')
    file_articles = os.path.join(tmp_path,'articles_file.csv')

    
    with open(file_model,"w+b") as local_model:
        local_model.write(inputblob.read())

    with open(file_clicks,"w+b") as local_csv:
        local_csv.write(inputblob2.read())
    
    with open(file_articles,"w+b") as art_csv:
        art_csv.write(inputblob3.read())

    
    df = pd.read_csv(file_clicks, ';')
    articles =pd.read_csv(file_articles,',')
    
  
    model = load_model(file_model)

    reader = Reader(rating_scale=(0, 1))
    data = Dataset.load_from_df(df[['user_id', 'category_id', 'rating']], reader)
    train_set, test_set = train_test_split(data, test_size=.25)
    predict = model.test(test_set)
    

    top_n = get_top_n(predict, n=5)

    req_body = req.get_json()
    name = req_body[0]['value']

    
    recommendation, categories = make_recommendation(int(name), top_n, df, articles)

    logging.info(f"Python blob trigger function processed blob \n"
                 f"Recommendation: {recommendation}\n"
                 f"cat: {categories}\n")
 
   

    response = {'recommendation': { 0:recommendation[0],1:recommendation[1],2:recommendation[2],3:recommendation[3],4:recommendation[4]}}
    if name:
        return func.HttpResponse(
            f"{response}",status_code=200)
            
    else:
        return func.HttpResponse(
           
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )
