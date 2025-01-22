import re
from urllib.parse import unquote

from django import template

register = template.Library()



@register.filter
def get_first_image_url(text):
    """Возвращает URL первого изображения из текста."""
    try:
        # Декодируем текст перед поиском
        decoded_text = unquote(text)
        # Регулярное выражение для поиска <img> тега и извлечения значения атрибута src
        img_regex = r'<img[^>]*src="([^"]+)"'
        match = re.search(img_regex, decoded_text)
        if match:
            return match.group(1)  # Возвращаем первую найденную ссылку на изображение
    except Exception as e:
        # Логируем ошибку для отладки (опционально)
        print(f"Ошибка при парсинге текста: {e}")

    return ''  # Возвращаем строку, если <img> не найден


@register.filter
def strip_html_and_content(text):
    """
    Убирает HTML-теги и их содержимое из текста, оставляя только чистый текст.
    """
    try:
        # Удаляем теги и их содержимое (например, <script>...</script>, <style>...</style>)
        text_without_big_tags = re.sub(r'<[^>]+>.*?</[^>]+>', '', text, flags=re.DOTALL)
        # Удаляем все оставшиеся одиночные теги
        text_without_samll_tags = re.sub(r'<[^>]+>', '', text_without_big_tags)
        clean_text = re.sub(r'<[^>]+.*?', '', text_without_samll_tags, flags=re.DOTALL)



        # Удаляем лишние пробелы
        clean_text = clean_text.strip()

        return clean_text
    except Exception as e:
        # Логируем ошибку для отладки
        print(f"Ошибка при обработке текста: {e}")
        return ''