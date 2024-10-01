// function updateUrl() {
//     const showMyTasksOnly = document.getElementById('showMyTasksOnlySwitch') ? document.getElementById('showMyTasksOnlySwitch').checked : null;
//     const sortOrder = document.getElementById('sortOrderSwitch') ? (document.getElementById('sortOrderSwitch').checked ? 'desc' : 'asc') : null;
//
//     const currentUrl = new URL(window.location.href);
//     const params = new URLSearchParams(currentUrl.search);
//
//     // Устанавливаем параметры
//     if (showMyTasksOnly) params.set('show_my_tasks_only', showMyTasksOnly);
//     if (sortOrder) params.set('sort_order', sortOrder);
//
//     // Обновляем URL
//     window.location.search = params.toString();
// }

function toggleFilter(filterName, currentValue, secondFilterName = null, secondFilterValue = null) {
    console.log(filterName, currentValue, secondFilterName, secondFilterValue)
    const urlParams = new URLSearchParams(window.location.search);

    // Логика для кнопки "Активные задачи"
    if (filterName === 'show_active_task') {
        // Всегда включаем активные и выключаем завершенные
        urlParams.set('show_active_task', 'true');
        urlParams.set('show_done_task', 'false');
    }

    // Логика для кнопки "Завершенные задачи"
    if (filterName === 'show_done_task') {
        // Всегда включаем завершенные и выключаем активные
        urlParams.set('show_done_task', 'true');
        urlParams.set('show_active_task', 'false');
    }

    // Логика для средней кнопки: включает обе группы, если хотя бы одна выключена
    if (secondFilterName && (currentValue === false || secondFilterValue === false)) {
        // Если хотя бы одна группа выключена, включаем обе
        urlParams.set('show_active_task', 'true');
        urlParams.set('show_done_task', 'true');
    }

    // Обновляем URL и перезагружаем страницу с новыми параметрами
    window.location.href = "?" + urlParams.toString();
}