// admin.js

// Set current year
document.addEventListener("DOMContentLoaded", () => {
    const yearElem = document.getElementById('year');
    if (yearElem) {
        yearElem.textContent = new Date().getFullYear();
    }
});

// Reset form
function undoChanges() {
    if (confirm('Are you sure you want to undo all your current changes?')) {
        const form = document.getElementById('adminSettingsForm');
        window.location.reload();
    }
}

function resetDefault() {
    if (confirm('Are you sure you want to reset all settings to system default?')) {
        fetch("/AI_reset", {
            method: "POST",
            body: "Reset",
        }).then((response) => {
            if (response.ok) {
                window.location.reload();
            }
        });
    }
}
