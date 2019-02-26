import os
import pickle
import json


import numpy as np
from sklearn import svm
from beeprint import pp

from config import Config
from data_loader import DataLoader
from data_loader import DataHelper
from models import text_GRU, text_CNN
from sklearn.metrics import classification_report
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score

RESULT_FILE = "./output/{}.json"



def svm_train(train_input, train_output):

    clf = svm.SVC(C=10.0, gamma='scale', kernel='rbf')

    clf.fit(train_input, np.argmax(train_output, axis=1))

    return clf

def svm_test(clf, test_input, test_output):

    probas = clf.predict(test_input)
    y_pred = probas
    y_true = np.argmax(test_output, axis=1)

    # To generate random scores
    # y_pred = np.random.randint(2, size=len(y_pred))
    
    result_string = classification_report(y_true, y_pred)
    print(confusion_matrix(y_true, y_pred))
    print(result_string)
    return classification_report(y_true, y_pred, output_dict=True), result_string




def train(model_name=None):

    # Load config
    config = Config()
    
    # Load data
    data = DataLoader(config)

    # Iterating over each fold
    results=[]
    for fold, (train_index, test_index) in enumerate(data.getStratifiedKFold()):

        # Present fold
        config.fold = fold+1
        print("Present Fold: {}".format(config.fold))

        # Prepare data
        train_input, train_output = data.getSplit(train_index)
        test_input, test_output = data.getSplit(test_index)
        datahelper = DataHelper(train_input, train_output, test_input, test_output, config, data)
        
        emb_matrix = datahelper.getEmbeddingMatrix()


        # Default text
        if (config.use_target_text) and (not config.use_target_audio): # Only text
            train_input = np.array([datahelper.pool_text(utt) for utt in datahelper.vectorizeUtterance(mode="train")])
            test_input = np.array([datahelper.pool_text(utt) for utt in datahelper.vectorizeUtterance(mode="test")])

        elif (config.use_target_audio) and (not config.use_target_text): # Only audio
            train_input = datahelper.getTargetAudioPool(mode="train")
            test_input = datahelper.getTargetAudioPool(mode="test")

        elif (config.use_target_text) and (config.use_target_audio): # Bimodal input
            train_input = np.array([datahelper.pool_text(utt) for utt in datahelper.vectorizeUtterance(mode="train")])
            test_input = np.array([datahelper.pool_text(utt) for utt in datahelper.vectorizeUtterance(mode="test")])

            train_input_audio = datahelper.getTargetAudioPool(mode="train")
            test_input_audio =  datahelper.getTargetAudioPool(mode="test")

            train_input = np.concatenate([train_input, train_input_audio], axis=1)
            test_input = np.concatenate([test_input, test_input_audio], axis=1)
        else:
            print("Invalid modalities")
            exit()


        # Aux input 

        if config.use_author:
            train_input_author = datahelper.getAuthor(mode="train")
            test_input_author =  datahelper.getAuthor(mode="test")

            train_input = np.concatenate([train_input, train_input_author], axis=1)
            test_input = np.concatenate([test_input, test_input_author], axis=1)

        if config.use_context:
            train_input_context = datahelper.getContextPool(mode="train")
            test_input_context =  datahelper.getContextPool(mode="test")

            train_input = np.concatenate([train_input, train_input_context], axis=1)
            test_input = np.concatenate([test_input, test_input_context], axis=1)

        
        train_output = datahelper.oneHotOutput(mode="train", size=config.num_classes)
        test_output = datahelper.oneHotOutput(mode="test", size=config.num_classes)

        clf = svm_train(train_input, train_output)
        result_dict, result_str = svm_test(clf, test_input, test_output)

        results.append(result_dict)
        

    
    # Dumping result to output
    if not os.path.exists(os.path.dirname(RESULT_FILE)):
        os.makedirs(os.path.dirname(RESULT_FILE))
    json.dump(results, open(RESULT_FILE.format(model_name), "wb"))



def printResult(model_name=None):

    results = json.load(open(RESULT_FILE.format(model_name), "rb"))

    weighted_fscores, macro_fscores, micro_fscores = [], [], []
    print("#"*20)
    for fold, result in enumerate(results):
        micro_fscores.append(result["micro avg"]["f1-score"])
        macro_fscores.append(result["macro avg"]["f1-score"])
        weighted_fscores.append(result["weighted avg"]["f1-score"])
        

        print("Fold {}:".format(fold+1))
        print("Micro Fscore: {}  Macro Fscore: {}  Weighted Fscore: {}".format(result["micro avg"]["f1-score"],
                                                                               result["macro avg"]["f1-score"],
                                                                               result["weighted avg"]["f1-score"]))
    print("#"*20)
    print("Avg :")
    print("Micro Fscore: {}  Macro Fscore: {}  Weighted Fscore: {}".format(np.mean(micro_fscores),
                                                                           np.mean(macro_fscores),
                                                                           np.mean(weighted_fscores)))


if __name__ == "__main__":

    '''
    model_names:
    - text_GRU
    - text_CNN
    '''
    MODEL = "SVM"
    RUNS = 1

    for _ in range(RUNS):
        train(model_name=MODEL)
        printResult(model_name=MODEL)