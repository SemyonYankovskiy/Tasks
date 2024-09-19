const modals = [];

function hideModals() {
    for (let i = 0; i < modals.length; i++) {
        modals[i].hide();
        modals.splice(i, 1);
    }
}

function closeModalsAndShowEdit(taskId) {
    hideModals();
    showEditModal(taskId);
}