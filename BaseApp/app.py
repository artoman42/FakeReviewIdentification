from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import requests
from bs4 import BeautifulSoup
import re
import numpy as np
from sentence_transformers import SentenceTransformer
import joblib

app = Flask(__name__)
CORS(app)

# Завантаження моделі та токенізатора
tokenizer = AutoTokenizer.from_pretrained('tabularisai/multilingual-sentiment-analysis')
model = AutoModelForSequenceClassification.from_pretrained('tabularisai/multilingual-sentiment-analysis')

sentence_transformer_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
XGBoostModel = joblib.load('../models/xgb_model.pkl')


def convert_numpy(o):
    """
    Recursively convert numpy types in lists or dicts to native python types.
    """
    if isinstance(o, np.integer):
        return int(o)
    elif isinstance(o, np.floating):
        return float(o)
    elif isinstance(o, list):
        return [convert_numpy(item) for item in o]
    elif isinstance(o, dict):
        return {k: convert_numpy(v) for k, v in o.items()}
    else:
        return o


def add_spaces_to_text(text):
    # Додавання пробілів між літерами та числами
    text = re.sub(r'(?<=[a-zа-яієїґ])(?=\d)', ' ', text)
    text = re.sub(r'(?<=\d)(?=[a-zа-яієїґ])', ' ', text)
    text = re.sub(r'(?=[A-ZА-ЯІЇЄҐ])(?=\d)', ' ', text)
    text = re.sub(r'(?<=\d)(?=[A-ZА-ЯІЇЄҐ])', ' ', text)
    # Додавання пробілів між великими і малими літерами
    text = re.sub(r'(?<=[a-zа-яієїґ])(?=[A-ZА-ЯІЇЄҐ])', ' ', text)
    # Додавання пробілів після крапки
    text = re.sub(r'(?<=\.)(?=[^\s])', ' ', text)
    return text


def find_comment_classes(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    elements_with_class = soup.find_all(class_=True)
    comment_classes_text = {}

    for element in elements_with_class:
        classes = element['class']
        text_content = element.get_text(strip=True)
        for class_name in classes:
            if 'product-comments__list-item' in class_name:
                if 'product-comments__list-item' not in comment_classes_text:
                    comment_classes_text['product-comments__list-item'] = []
                if text_content:
                    comment_classes_text['product-comments__list-item'].append(text_content)

    if not comment_classes_text.get('product-comments__list-item'):
        for element in elements_with_class:
            classes = element['class']
            text_content = element.get_text(strip=True)
            for class_name in classes:
                if 'product-comment__item-text' in class_name:
                    if 'product-comment__item-text' not in comment_classes_text:
                        comment_classes_text['product-comment__item-text'] = []
                    if text_content:
                        comment_classes_text['product-comment__item-text'].append(text_content)
    return comment_classes_text


def extract_product_name_from_title(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    title_element = soup.find('h1', class_='page__title')
    if title_element:
        return title_element.get_text(strip=True)
    return "Назва товару не знайдена"


def extract_product_name_from_h2(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    h2_element = soup.find('h1', class_='h2 bold ng-star-inserted')
    if h2_element:
        return h2_element.get_text(strip=True)
    return "Назва товару не знайдена"


def preprocess_text(text):
    # Видалення зайвого тексту на початку відгуку
    pattern = r'^(\w+(?:\s\w+)*)\s(\d{2}\s\w+\s\d{4}\s)?(Відгук від покупця\.\s)?(покупця\.\s)?(Продавець: .*?\.\s)?(Розмір: .*?)?(Об\'єм: .*? мл)?'
    text = re.sub(pattern, '', text)
    # Видалення тексту відповіді на відгук
    text = re.sub(r'Відповісти\s?\d+.*$', '', text)
    return text.strip()


def extract_nickname(text):
    match = re.match(r'^(\w+(?:\s\w+)*?)\s\d{2}', text)
    if match:
        return match.group(1).strip()
    return "Невідомий"


def extract_nicknames_from_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    elements_with_class = soup.find_all('div', class_='product-comment__item-title')
    nicknames = [element.get_text(strip=True) for element in elements_with_class]
    return nicknames


def analyze_sentiment(review_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/124.0.0.0 Safari/537.36'}
    response = requests.get(review_url, headers=headers)
    html_content = response.text
    comments = find_comment_classes(html_content)
    sentiments = []
    product_name = None

    if 'product-comments__list-item' in comments:
        product_name = extract_product_name_from_h2(html_content)
        for text_content in comments['product-comments__list-item']:
            text_content_with_spaces = add_spaces_to_text(text_content)
            nickname = extract_nickname(text_content_with_spaces)
            clean_text = preprocess_text(text_content_with_spaces)
            emb_for_fake_detection = sentence_transformer_model.encode(clean_text)
            if len(clean_text) < 1024:
                tokens = tokenizer.encode(clean_text, return_tensors='pt')
                result = model(tokens)
                sentiment = int(torch.argmax(result.logits)) + 1
                fake_scores = XGBoostModel.predict_proba([emb_for_fake_detection])
                fake_class = int(np.argmax(fake_scores[0]))
                sentiments.append({
                    'nickname': nickname,
                    'text': clean_text,
                    'sentiment': sentiment,
                    'fake_class': fake_class,
                    'fake_score': float(fake_scores[0][fake_class])
                })
            else:
                sentiments.append({
                    'nickname': nickname,
                    'text': clean_text,
                    'sentiment': 'Текст перевищує 512 символів, аналіз не виконується.'
                })
    elif 'product-comment__item-text' in comments:
        product_name = extract_product_name_from_title(html_content)
        nicknames = extract_nicknames_from_html(html_content)
        for i, text_content in enumerate(comments['product-comment__item-text']):
            nickname = nicknames[i] if i < len(nicknames) else 'Невідомий'
            clean_text = preprocess_text(text_content)
            emb_for_fake_detection = sentence_transformer_model.encode(clean_text)
            if len(text_content) < 1024:
                tokens = tokenizer.encode(clean_text, return_tensors='pt')
                result = model(tokens)
                sentiment = int(torch.argmax(result.logits)) + 1
                fake_scores = XGBoostModel.predict_proba([emb_for_fake_detection])
                fake_class = int(np.argmax(fake_scores[0]))
                sentiments.append({
                    'nickname': nickname,
                    'text': clean_text,
                    'sentiment': sentiment,
                    'fake_class': fake_class,
                    'fake_score': float(fake_scores[0][fake_class])
                })
            else:
                sentiments.append({
                    'nickname': nickname,
                    'text': clean_text,
                    'sentiment': 'Текст перевищує 512 символів, аналіз не виконується.'
                })

    overall_sentiment = calculate_overall_sentiment(sentiments)
    recommendation = ("Цей товар - є гарною опцією і рекомендований системою для купівлі на основі відгуків."
                      if overall_sentiment > 3.2 else
                      "Цей товар - не рекомендований системою для купівлі на основі відгуків.")
    return sentiments, overall_sentiment, recommendation, product_name


def calculate_overall_sentiment(sentiments):
    scores = [s['sentiment'] for s in sentiments if isinstance(s['sentiment'], int)]
    if scores:
        overall_sentiment = np.mean(scores)
    else:
        overall_sentiment = 'N/A'
    return overall_sentiment


def sentiment_distribution(sentiments):
    distribution = {i: 0 for i in range(1, 6)}
    for s in sentiments:
        if isinstance(s['sentiment'], int):
            distribution[s['sentiment']] += 1
    return distribution


def calculate_clean_sentiment(sentiments):
    """Calculate overall sentiment and distribution filtering out fake and AI-generated reviews."""
    clean_scores = [s['sentiment'] for s in sentiments 
                    if isinstance(s['sentiment'], int) and s.get('fake_class', 0) == 0]
    if clean_scores:
        overall_clean = np.mean(clean_scores)
    else:
        overall_clean = 'N/A'
    clean_distribution = {i: 0 for i in range(1, 6)}
    for s in sentiments:
        if isinstance(s['sentiment'], int) and s.get('fake_class', 0) == 0:
            clean_distribution[s['sentiment']] += 1
    return overall_clean, clean_distribution


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    review_link = data['reviewLink']
    sentiments, overall_sentiment, recommendation, product_name = analyze_sentiment(review_link)
    distribution = sentiment_distribution(sentiments)

    clean_overall_sentiment, clean_distribution = calculate_clean_sentiment(sentiments)

    response_data = {
        'results': sentiments,
        'overall_sentiment': overall_sentiment,
        'distribution': distribution,
        'recommendation': recommendation,
        'product_name': product_name,
        'clean_overall_sentiment': clean_overall_sentiment,
        'clean_distribution': clean_distribution
    }
    
    converted_response = convert_numpy(response_data)
    return jsonify(converted_response)


if __name__ == '__main__':
    app.run(debug=True)

