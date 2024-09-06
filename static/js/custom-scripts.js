

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
        var textContent = spoilerTextElement.innerText || spoilerTextElement.textContent;
        if (textContent.length > 500) {
            var visibleText = textContent.substring(0, 500) + '...';
            spoilerTextElement.innerText = visibleText;
            toggleSpoilerButton.style.display = 'block';
            toggleSpoilerButton.addEventListener('click', function() {
                if (spoilerTextElement.classList.contains('spoiler')) {
                    spoilerTextElement.classList.remove('spoiler');
                    toggleSpoilerButton.innerText = 'Показать больше';
                    spoilerTextElement.innerText = visibleText;
                } else {
                    spoilerTextElement.classList.add('spoiler');
                    toggleSpoilerButton.innerText = 'Скрыть';
                    spoilerTextElement.innerText = textContent;
                }
            });
        } else {
            toggleSpoilerButton.style.display = 'none';
        }
    });
});
