import os
import json
from dotenv import load_dotenv
from transformers import pipeline
from nltk.tokenize import word_tokenize
from sklearn.linear_model import LogisticRegression
from botFunc import conversation_state
from dotenv import load_dotenv
from transformers import pipeline
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
import json
from nltk.corpus import wordnet
import random
from nltk.tokenize import word_tokenize
from nltk import download
from sklearn.utils import resample
from shortcuts import shortcuts_map, ps

download('wordnet')
download('punkt')
load_dotenv()
import pyttsx3
def augment_text(text, num_augmented=1):
    words = word_tokenize(text)
    augmented_texts = []
    
    for _ in range(num_augmented):
        new_words = words.copy()
        word_idx = random.randint(0, len(words) - 1)
        synonym_list = wordnet.synsets(words[word_idx])
        
        if synonym_list:
            synonym = random.choice(synonym_list).lemmas()[0].name()
            if synonym != words[word_idx]:
                new_words[word_idx] = synonym
                augmented_texts.append(' '.join(new_words))
    
    return augmented_texts

def load_and_train_model():
    with open('data.json', 'r') as f:
        data = json.load(f)

    df = pd.DataFrame(data)

    max_class_size = df['intent'].value_counts().max()
    df_balanced = pd.concat([
        resample(df[df['intent'] == intent], replace=True, n_samples=max_class_size, random_state=42)
        for intent in df['intent'].unique()
    ])
    df_balanced = df_balanced.sample(frac=1, random_state=42).reset_index(drop=True)

    augmented_data = []
    for _, row in df_balanced.iterrows():
        text = row['text']
        intent = row['intent']
        augmented_texts = augment_text(text, num_augmented=3) 
        augmented_data.extend([(text, intent) for text in augmented_texts])

    augmented_df = pd.DataFrame(augmented_data, columns=['text', 'intent'])
    df_augmented = pd.concat([df_balanced, augmented_df]).drop_duplicates().reset_index(drop=True)

    X = df_augmented['text']
    y = df_augmented['intent']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    pipeline = Pipeline([
        ('vectorizer', TfidfVectorizer(lowercase=True, stop_words='english', ngram_range=(1, 2), max_features=5000)),
        ('classifier', LogisticRegression(max_iter=1000))
    ])

    param_grid = {
        'classifier__C': [0.1, 1, 10, 100],
        'classifier__solver': ['liblinear', 'saga'],
    }

    grid_search = GridSearchCV(pipeline, param_grid, cv=5, scoring='accuracy')
    grid_search.fit(X_train, y_train)
    bot_model = grid_search.best_estimator_
    return  grid_search.best_estimator_


bot_model = load_and_train_model()

def preprocess_query(query):
    tokens = word_tokenize(query.lower())
    stemmed_tokens = [ps.stem(token) for token in tokens]
    return set(stemmed_tokens)

def determine_intent(query):
    query = query.lower().strip() 
    predicted_intent = bot_model.predict([query])
    return predicted_intent[0]
