import logging
import os
from readline import append_history_file
import tempfile
import azure.functions as func
import pandas as pd
import random
from random import randint
import pickle
from collections import defaultdict
from urllib.parse import parse_qs
import numpy as np
from scipy.spatial import distance
import json


def getFiveArticles(e, userId, df):
    
    #logging.info(f"Debut function getfive articles\n e:{e.length}\n userId:{userId}\ndf:{df.shape}")

    ee=e
    #Je regarde tout les articles lues par l'utilisateurs
    var = df.loc[df['user_id']==userId]['click_article_id'].tolist()
    
    logging.info(f'var loadée\n var: {var}')
  
    #j'en choisie un aléatoirement
    value = randint(0, len(var))

    logging.info(f'value loaded\n vallue: {value}')

    #On supprime de la matrice tout les articles lue sauf celui selectionné
    for i in range(0, len(var)):
        if i != value:
            ee=np.delete(ee,[i],0)
    arr=[]
    
    #On supprime l' article de la nouvelle martrice
    f=np.delete(ee,[value],0)
    

    #On selectionne 5 article les plus proches de celui selectionné
    for i in range(0,5):
        distances = distance.cdist([ee[value]], f, "cosine")[0]
        min_index = np.argmin(distances)
        f=np.delete(f,[min_index],0)
        
        #On cherche la matrice correspondante dans la matrice originale. 
        result = np.where(e == f[min_index])
        arr.append(int(result[0][0]))
        
    return arr


def main(inputblob: func.InputStream, inputblob2: func.InputStream, req: func.HttpRequest, ) -> func.HttpResponse:

    logging.info('Python HTTP trigger function processed a request.')

    tmp_path = tempfile.gettempdir()
    file_model = os.path.join(tmp_path,'model.pickle')
    file_clicks = os.path.join(tmp_path,'clicks_file.csv')

    logging.info('prepare to load file model')

    with open(file_model,"w+b") as local_model:
        local_model.write(inputblob.read())
    local_model.close()   

    
    with open(file_clicks,"w+b") as local_csv:
        local_csv.write(inputblob2.read())
    local_csv.close()

    logging.info(f'files are writting to temp')
    
    df = pd.read_csv(file_clicks, ';')

    logging.info(f'data frame read Ok \n dataframe: {df.head(3)}')
    
   
    req_body = req.get_json()
    name = req_body[0]['value']

    logging.info(f'user id received: {name}')

    e = pd.read_pickle(file_model)
    
    logging.info(f'endebed_matrice read and load')

    recommendation = getFiveArticles(e, int(name),df)
    #reponse au format json

    response = {"livre 1":int(recommendation[0]),"livre 2":int(recommendation[1]),"livre 3":int(recommendation[2]),"livre 4":recommendation[3],"livre 5":recommendation[4]}
    #x = {"name": "Paul","age": int(recommendation[0]),"city": "Lille"}
    test = json.dumps(recommendation)
    logging.info(f'recommandation: {test}')
    if name:
        return func.HttpResponse(
            body=test
            ,status_code=200)   
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )
