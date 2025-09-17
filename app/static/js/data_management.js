// Data Management Module
const DataManager = (function() {
    'use strict';

    // Private variables
    let loadingModal, successModal, errorModal;
    let progressInterval = null;
    let currentProgress = 0;

    // Initialize function
    function init() {
        // Initialize Bootstrap modals
        const loadingModalEl = document.getElementById('loadingModal');
        const successModalEl = document.getElementById('successModal');
        const errorModalEl = document.getElementById('errorModal');

        if (loadingModalEl) {
            loadingModal = new bootstrap.Modal(loadingModalEl, {
                backdrop: 'static',
                keyboard: false
            });
        }

        if (successModalEl) {
            successModal = new bootstrap.Modal(successModalEl);
        }

        if (errorModalEl) {
            errorModal = new bootstrap.Modal(errorModalEl);
        }

        // Setup event listeners
        setupImportHandler();
        setupExportButtons();
    }

    // Setup import file handler
    function setupImportHandler() {
        const importFile = document.getElementById('importFile');
        const importForm = document.getElementById('importForm');

        if (importFile && importForm) {
            importFile.addEventListener('change', function() {
                if (this.files.length > 0) {
                    handleFileImport(this.files[0], importForm);
                }
            });
        }
    }

    // Setup export buttons
    function setupExportButtons() {
        const exportMyBtn = document.getElementById('exportMyBtn');
        const exportAllBtn = document.getElementById('exportAllBtn');

        if (exportMyBtn) {
            exportMyBtn.addEventListener('click', () => exportUnits('my'));
        }

        if (exportAllBtn) {
            exportAllBtn.addEventListener('click', () => exportUnits('all'));
        }
    }

    // Handle file import
    function handleFileImport(file, form) {
        const fileName = file.name;
        const fileSize = (file.size / 1024).toFixed(2); // KB

        // Update loading modal text
        updateLoadingModal('Importing Units...', `Processing ${fileName} (${fileSize} KB)`);

        // Show modal and start progress
        showLoadingModal();
        startProgress(85);

        // Submit form after small delay
        setTimeout(() => {
            form.submit();
        }, 100);
    }

    // Export units with AJAX
    async function exportUnits(type) {
        const exportMyBtn = document.getElementById('exportMyBtn');
        const exportAllBtn = document.getElementById('exportAllBtn');

        // Disable buttons
        if (exportMyBtn) exportMyBtn.disabled = true;
        if (exportAllBtn) exportAllBtn.disabled = true;

        const exportTypeText = type === 'my' ? 'Your Units' : 'All Units';

        // Update loading modal
        updateLoadingModal(`Exporting ${exportTypeText}...`, 'Preparing your download, please wait...');
        showLoadingModal();
        startProgress(80);

        try {
            // AJAX request using fetch API
            const response = await fetch(getExportUrl(type));

            if (!response.ok) {
                throw new Error(`Export failed: ${response.statusText}`);
            }

            // Update progress
            updateLoadingModal(`Exporting ${exportTypeText}...`, 'Processing data...');
            currentProgress = 80;
            startProgress(95);

            // Get filename from response headers
            const filename = extractFilename(response.headers);

            // Get the blob (file data)
            const blob = await response.blob();

            // Update to completion
            updateLoadingModal(`Exporting ${exportTypeText}...`, 'Finalising download...');

            // Complete and download
            completeProgressAndHide(() => {
                downloadFile(blob, filename);
                showSuccessMessage('Export Complete!',
                    `${exportTypeText} have been exported successfully as ${filename}`);
            });

        } catch (error) {
            console.error('Export error:', error);
            hideLoadingModal();
            showErrorMessage(`Failed to export units: ${error.message}`);
        } finally {
            // Re-enable buttons
            setTimeout(() => {
                if (exportMyBtn) exportMyBtn.disabled = false;
                if (exportAllBtn) exportAllBtn.disabled = false;
            }, 2000);
        }
    }

    // Progress bar management
    function resetProgress() {
        currentProgress = 0;
        updateProgressBar(0);
    }

    function updateProgressBar(percent) {
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');

        if (progressBar && progressText) {
            progressBar.style.width = percent + '%';
            progressBar.setAttribute('aria-valuenow', percent);
            progressText.textContent = percent + '%';
        }
    }

    function startProgress(maxProgress = 90) {
        stopProgress();

        progressInterval = setInterval(() => {
            if (currentProgress < maxProgress) {
                const increment = Math.max(1, Math.floor((maxProgress - currentProgress) / 10));
                currentProgress = Math.min(currentProgress + increment, maxProgress);
                updateProgressBar(currentProgress);
            }
        }, 200);
    }

    function stopProgress() {
        if (progressInterval) {
            clearInterval(progressInterval);
            progressInterval = null;
        }
    }

    function completeProgressAndHide(callback) {
        stopProgress();

        let fastProgress = currentProgress;
        const fastInterval = setInterval(() => {
            fastProgress = Math.min(fastProgress + 10, 100);
            updateProgressBar(fastProgress);

            if (fastProgress >= 100) {
                clearInterval(fastInterval);

                // Hide spinner
                const spinner = document.getElementById('spinnerContainer');
                if (spinner) spinner.style.display = 'none';

                setTimeout(() => {
                    hideLoadingModal();
                    if (callback) setTimeout(callback, 300);
                }, 500);
            }
        }, 30);
    }

    // Modal management
    function showLoadingModal() {
        resetProgress();
        const spinner = document.getElementById('spinnerContainer');
        if (spinner) spinner.style.display = 'block';
        if (loadingModal) loadingModal.show();
    }

    function hideLoadingModal() {
        stopProgress();

        if (loadingModal) {
            loadingModal.hide();
        }

        // Clean up any lingering backdrops
        setTimeout(() => {
            const backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(backdrop => backdrop.remove());
            document.body.classList.remove('modal-open');
            document.body.style = '';
        }, 100);
    }

    function updateLoadingModal(title, subtitle) {
        const loadingText = document.getElementById('loadingText');
        const loadingSubtext = document.getElementById('loadingSubtext');

        if (loadingText) loadingText.textContent = title;
        if (loadingSubtext) loadingSubtext.textContent = subtitle;
    }

    function showSuccessMessage(title, message) {
        const successTitle = document.getElementById('successTitle');
        const successMessage = document.getElementById('successMessage');

        if (successTitle) successTitle.textContent = title;
        if (successMessage) successMessage.textContent = message;
        if (successModal) successModal.show();
    }

    function showErrorMessage(message) {
        const errorMessage = document.getElementById('errorMessage');

        if (errorMessage) errorMessage.textContent = message;
        if (errorModal) setTimeout(() => errorModal.show(), 500);
    }

    // Utility functions
    function getExportUrl(type) {
        // These URLs will be set from the template
        return type === 'my' ? window.EXPORT_MY_URL : window.EXPORT_ALL_URL;
    }

    function extractFilename(headers) {
        const disposition = headers.get('Content-Disposition');
        let filename = 'units_export.csv';

        if (disposition) {
            const matches = /filename="(.+)"/.exec(disposition);
            if (matches && matches[1]) {
                filename = matches[1];
            }
        }

        return filename;
    }

    function downloadFile(blob, filename) {
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();

        setTimeout(() => {
            window.URL.revokeObjectURL(downloadUrl);
            document.body.removeChild(a);
        }, 100);
    }

    // Public API
    return {
        init: init,
        exportUnits: exportUnits
    };
})();

// Initialise when DOM is ready
document.addEventListener('DOMContentLoaded', DataManager.init);