import os
import re
import requests
import json
from google.cloud import translate_v2 as translate
from bs4 import BeautifulSoup

current_directory = os.path.dirname(os.path.abspath(__file__))

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join(current_directory, 'eastern-archive-424609-f2-0c8886450710.json')

def initialize_translate_client():
    return translate.Client()

def translate_terms(client, terms, source_language, target_language):
    translations = {}
    for term in terms:
        try:
            result = client.translate(term, source_language=source_language, target_language=target_language)
            translations[term] = result['translatedText']
        except Exception as e:
            print(f"Ошибка перевода термина '{term}': {e}")
            translations[term] = "Перевод не найден"
    return translations

def read_terms(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return [line.strip() for line in file.readlines()]
    except FileNotFoundError:
        print(f"Файл {file_path} не найден.")
        return []
    except Exception as e:
        print(f"Ошибка при чтении файла {file_path}: {e}")
        return []

def get_cleaned_wikipedia_article(term, language='ky'):
    search_url = f"https://{language}.wikipedia.org/w/api.php"
    search_params = {
        'action': 'query',
        'list': 'search',
        'srsearch': term,
        'utf8': '',
        'format': 'json',
    }
    try:
        search_response = requests.get(search_url, params=search_params)
        search_response.raise_for_status()
        search_results = search_response.json().get('query', {}).get('search', [])
        if not search_results:
            return "Не удалось найти статью на данную тему"
        
        pageid = search_results[0]['pageid']
        page_url = f"https://{language}.wikipedia.org/w/api.php"
        page_params = {
            'action': 'query',
            'prop': 'extracts',
            'explaintext': True,
            'pageids': pageid,
            'format': 'json',
        }
        page_response = requests.get(page_url, params=page_params)
        page_response.raise_for_status()
        page_data = page_response.json()
        page_content = page_data['query']['pages'][str(pageid)]['extract']

        page_content = page_content.replace("\n", "")
        
        page_content = re.sub(r'\([^)]*\)', '', page_content)
        
        page_content = re.sub(r'\d+', lambda x: number_to_words(int(x.group())), page_content)
        
        return page_content
    except Exception as e:
        print(f"Ошибка получения статьи для термина '{term}': {e}")
        return "Не удалось найти статью на данную тему"

def number_to_words(number):
    units = ['ноль', 'бир', 'эки', 'уч', 'төрт', 'беш', 'алты', 'жети', 'сегиз', 'тогуз']
    teens = ['он', 'жыйырма', 'отуз', 'кырк', 'элүү', 'алтымыш', 'жетимиш', 'сексен', 'токсон']
    tens = ['', 'он', 'жыйырма', 'отуз', 'кырк', 'элүү', 'алтымыш', 'жетимиш', 'сексен', 'токсон']

    if number < 10:
        return units[number]
    elif number < 20:
        return teens[number - 10]
    elif number < 100:
        return tens[number // 10] + ('' if number % 10 == 0 else ' ') + units[number % 10]
    elif number < 1000:
        return units[number // 100] + ' жүз' + (' ' + number_to_words(number % 100) if number % 100 != 0 else '')
    elif number < 10000:
        return units[number // 1000] + ' мын' + (' ' + number_to_words(number % 1000) if number % 1000 != 0 else '')
    else:
        return 'Сан сыяктырды'

def save_dictionary(dictionary, file_path):
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(dictionary, file, ensure_ascii=False, indent=4)
        print(f"Словарь успешно сохранен в файл '{file_path}'.")
    except Exception as e:
        print(f"Ошибка при сохранении словаря в файл {file_path}: {e}")

def main():
    try:
        client = initialize_translate_client()
    except Exception as e:
        print(f"Ошибка инициализации клиента перевода: {e}")
        return

    russian_terms_file = os.path.join(current_directory, 'technical_terms.txt')
    russian_terms = read_terms(russian_terms_file)
    if not russian_terms:
        print("Нет терминов для перевода.")
        return

    technical_dictionary = translate_terms(client, russian_terms, 'ru', 'ky')
    
    articles_dictionary = {}
    for term, translated_term in technical_dictionary.items():
        if translated_term != "Перевод не найден":
            articles_dictionary[term] = {
                'translation': translated_term,
                'article': get_cleaned_wikipedia_article(translated_term)
            }
        else:
            articles_dictionary[term] = {
                'translation': translated_term,
                'article': "Не удалось найти статью на данную тему"
            }

    output_file_path = os.path.join(current_directory, 'technical_dictionary_with_articles.json')
    save_dictionary(articles_dictionary, output_file_path)

if __name__ == "__main__":
    main()
