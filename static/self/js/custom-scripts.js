

// Script for initializing Bootstrap tooltips
document.addEventListener('DOMContentLoaded', function () {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});


// Script for handling spoiler text
document.addEventListener('DOMContentLoaded', function() {
    var spoilerTextElements = document.querySelectorAll('.spoiler-text');
    spoilerTextElements.forEach(function(spoilerTextElement) {
        var toggleSpoilerButton = spoilerTextElement.nextElementSibling;
        var textContent = spoilerTextElement.textContent;

        // Для подсчета длины заменяем все переносы строк на два символа
        var contentLength = textContent.replace(/\n/g, '\n\n').length;

        if (contentLength > 500) {
            // Находим видимую часть текста (первые 500 символов)
            var visibleText = textContent.substring(0, 500) + '...';

            // Показываем укороченный текст, но с сохранением форматирования (переносы строк сохраняются)
            spoilerTextElement.textContent = visibleText;
            toggleSpoilerButton.style.display = 'block';

            toggleSpoilerButton.addEventListener('click', function() {
                if (spoilerTextElement.classList.contains('spoiler')) {
                    spoilerTextElement.classList.remove('spoiler');
                    toggleSpoilerButton.innerText = 'Показать больше';
                    spoilerTextElement.textContent = visibleText;
                } else {
                    spoilerTextElement.classList.add('spoiler');
                    toggleSpoilerButton.innerText = 'Скрыть';
                    spoilerTextElement.textContent = textContent;
                }
            });
        } else {
            toggleSpoilerButton.style.display = 'none';
        }
    });
});
