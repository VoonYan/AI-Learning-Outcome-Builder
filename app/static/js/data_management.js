/**
 * Data Management Module
 *
 * Handles import/export operations for units and learning outcomes.
 * Uses the Module Pattern for encapsulation and provides a clean public API.
 *
 * Features:
 * - File import with progress tracking
 * - CSV export for user's units or all units
 * - Modal management for user feedback
 * - Progress bar animation for long operations
 * - AJAX-based operations to prevent page reloads
 *
 * Dependencies:
 * - Bootstrap 5 for modals and UI components
 * - Server endpoints set via global variables (EXPORT_MY_URL, EXPORT_ALL_URL)
 *
 * @module DataManager
 */
const DataManager = (function() {
    'use strict';

    // ==================== PRIVATE VARIABLES ====================

    // Bootstrap modal instances
    let loadingModal, successModal, errorModal;

    // Progress tracking
    let progressInterval = null;  // Interval for progress animation
    let currentProgress = 0;       // Current progress percentage

    // ==================== INITIALIZATION ====================

    /**
     * Initialize the Data Manager module
     * Sets up Bootstrap modals and event listeners for import/export
     * Called automatically when DOM is ready
     */
    function init() {
        // Initialize Bootstrap modals
        const loadingModalEl = document.getElementById('loadingModal');
        const successModalEl = document.getElementById('successModal');
        const errorModalEl = document.getElementById('errorModal');

        // Create Bootstrap modal instances if elements exist
        if (loadingModalEl) {
            loadingModal = new bootstrap.Modal(loadingModalEl, {
                backdrop: 'static',  // Prevent closing by clicking outside
                keyboard: false      // Prevent closing with ESC key
            });
        }

        if (successModalEl) {
            successModal = new bootstrap.Modal(successModalEl);
        }

        if (errorModalEl) {
            errorModal = new bootstrap.Modal(errorModalEl);
        }

        // Setup event listeners for import/export functionality
        setupImportHandler();
        setupExportButtons();
    }

    // ==================== FILE IMPORT ====================

    /**
     * Setup file import handler
     * Listens for file selection and triggers import process
     */
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

    /**
     * Handle file import process
     * Shows loading modal with file info and submits form
     *
     * @param {File} file - Selected file object
     * @param {HTMLFormElement} form - Form element to submit
     */
    function handleFileImport(file, form) {
        const fileName = file.name;
        const fileSize = (file.size / 1024).toFixed(2); // Convert to KB

        // Update loading modal with file information
        updateLoadingModal(
            'Importing Units...',
            `Processing ${fileName} (${fileSize} KB)`
        );

        // Show modal and start progress animation
        showLoadingModal();
        startProgress(85); // Progress to 85% during processing

        // Submit form after small delay to ensure modal is visible
        setTimeout(() => {
            form.submit();
        }, 100);
    }

    // ==================== FILE EXPORT ====================

    /**
     * Setup export button event listeners
     * Handles both "Export My Units" and "Export All Units" buttons
     */
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

    /**
     * Export units as CSV file
     * Fetches CSV data from server and triggers download
     *
     * @param {string} type - Export type: 'my' for user's units, 'all' for all units
     * @async
     */
    async function exportUnits(type) {
        const exportMyBtn = document.getElementById('exportMyBtn');
        const exportAllBtn = document.getElementById('exportAllBtn');

        // Disable buttons during export to prevent multiple requests
        if (exportMyBtn) exportMyBtn.disabled = true;
        if (exportAllBtn) exportAllBtn.disabled = true;

        // Determine export type text for UI
        const exportTypeText = type === 'my' ? 'Your Units' : 'All Units';

        try {
            // Show loading modal
            updateLoadingModal('Exporting Units...', `Preparing ${exportTypeText} for download`);
            showLoadingModal();
            startProgress(90);

            // Get appropriate export URL
            const url = getExportUrl(type);

            // Fetch CSV data from server
            const response = await fetch(url);

            if (!response.ok) {
                throw new Error('Export failed');
            }

            // Convert response to blob for download
            const blob = await response.blob();

            // Extract filename from response headers or use default
            const filename = extractFilename(response.headers) ||
                            `units_export_${type}_${Date.now()}.csv`;

            // Trigger file download
            downloadFile(blob, filename);

            // Complete progress and show success
            completeProgressAndHide(() => {
                showSuccessMessage('Export Successful',
                    `${exportTypeText} have been exported successfully.`);
            });

        } catch (error) {
            console.error('Export error:', error);

            // Hide loading and show error
            completeProgressAndHide(() => {
                showErrorMessage('Export failed. Please try again.');
            });
        } finally {
            // Re-enable buttons
            if (exportMyBtn) exportMyBtn.disabled = false;
            if (exportAllBtn) exportAllBtn.disabled = false;
        }
    }

    // ==================== PROGRESS MANAGEMENT ====================

    /**
     * Update progress bar display
     * @param {number} percent - Progress percentage (0-100)
     */
    function updateProgressBar(percent) {
        const progressBar = document.getElementById('progressBar');
        if (progressBar) {
            progressBar.style.width = percent + '%';
            progressBar.setAttribute('aria-valuenow', percent);

            // Update text if element exists
            const progressText = document.getElementById('progressText');
            if (progressText) {
                progressText.textContent = Math.round(percent) + '%';
            }
        }
    }

    /**
     * Reset progress to 0
     */
    function resetProgress() {
        currentProgress = 0;
        updateProgressBar(0);
    }

    /**
     * Start animated progress
     * Gradually increases progress to specified maximum
     *
     * @param {number} maxProgress - Maximum progress percentage to reach
     */
    function startProgress(maxProgress = 90) {
        resetProgress();

        // Clear any existing interval
        if (progressInterval) {
            clearInterval(progressInterval);
        }

        // Animate progress bar
        progressInterval = setInterval(() => {
            if (currentProgress < maxProgress) {
                // Slow down as we approach the maximum
                const increment = Math.max(0.5, (maxProgress - currentProgress) / 10);
                currentProgress = Math.min(currentProgress + increment, maxProgress);
                updateProgressBar(currentProgress);
            }
        }, 200); // Update every 200ms
    }

    /**
     * Stop progress animation
     */
    function stopProgress() {
        if (progressInterval) {
            clearInterval(progressInterval);
            progressInterval = null;
        }
    }

    /**
     * Complete progress to 100% and hide modal
     * Quickly animates to 100% before hiding
     *
     * @param {Function} callback - Optional callback after modal is hidden
     */
    function completeProgressAndHide(callback) {
        stopProgress();

        let fastProgress = currentProgress;

        // Quickly complete to 100%
        const fastInterval = setInterval(() => {
            fastProgress = Math.min(fastProgress + 10, 100);
            updateProgressBar(fastProgress);

            if (fastProgress >= 100) {
                clearInterval(fastInterval);

                // Hide spinner if exists
                const spinner = document.getElementById('spinnerContainer');
                if (spinner) spinner.style.display = 'none';

                // Wait briefly then hide modal
                setTimeout(() => {
                    hideLoadingModal();
                    if (callback) setTimeout(callback, 300);
                }, 500);
            }
        }, 30); // Fast animation
    }

    // ==================== MODAL MANAGEMENT ====================

    /**
     * Show loading modal with progress bar
     */
    function showLoadingModal() {
        resetProgress();

        // Show spinner
        const spinner = document.getElementById('spinnerContainer');
        if (spinner) spinner.style.display = 'block';

        // Show modal
        if (loadingModal) loadingModal.show();
    }

    /**
     * Hide loading modal and clean up
     */
    function hideLoadingModal() {
        stopProgress();

        if (loadingModal) {
            loadingModal.hide();
        }

        // Clean up any lingering Bootstrap backdrops
        // Sometimes Bootstrap leaves backdrops after modal is hidden
        setTimeout(() => {
            const backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(backdrop => backdrop.remove());

            // Reset body classes that Bootstrap adds
            document.body.classList.remove('modal-open');
            document.body.style = '';
        }, 100);
    }

    /**
     * Update loading modal text
     *
     * @param {string} title - Main loading message
     * @param {string} subtitle - Additional details
     */
    function updateLoadingModal(title, subtitle) {
        const loadingText = document.getElementById('loadingText');
        const loadingSubtext = document.getElementById('loadingSubtext');

        if (loadingText) loadingText.textContent = title;
        if (loadingSubtext) loadingSubtext.textContent = subtitle;
    }

    /**
     * Show success modal with custom message
     *
     * @param {string} title - Success title
     * @param {string} message - Success message details
     */
    function showSuccessMessage(title, message) {
        const successTitle = document.getElementById('successTitle');
        const successMessage = document.getElementById('successMessage');

        if (successTitle) successTitle.textContent = title;
        if (successMessage) successMessage.textContent = message;
        if (successModal) successModal.show();
    }

    /**
     * Show error modal with custom message
     *
     * @param {string} message - Error message to display
     */
    function showErrorMessage(message) {
        const errorMessage = document.getElementById('errorMessage');

        if (errorMessage) errorMessage.textContent = message;

        // Small delay to ensure previous modal is hidden
        if (errorModal) setTimeout(() => errorModal.show(), 500);
    }

    // ==================== UTILITY FUNCTIONS ====================

    /**
     * Get export URL based on type
     * URLs are set globally by the template
     *
     * @param {string} type - Export type ('my' or 'all')
     * @returns {string} Export endpoint URL
     */
    function getExportUrl(type) {
        // These URLs are set from the template via global variables
        return type === 'my' ? window.EXPORT_MY_URL : window.EXPORT_ALL_URL;
    }

    /**
     * Extract filename from Content-Disposition header
     *
     * @param {Headers} headers - Response headers
     * @returns {string} Extracted filename or default
     */
    function extractFilename(headers) {
        const disposition = headers.get('Content-Disposition');
        let filename = 'units_export.csv';

        if (disposition) {
            // Parse filename from header
            // Format: attachment; filename="units_and_outcomes.csv"
            const matches = /filename="(.+)"/.exec(disposition);
            if (matches && matches[1]) {
                filename = matches[1];
            }
        }

        return filename;
    }

    /**
     * Trigger file download in browser
     * Creates a temporary download link and clicks it programmatically
     *
     * @param {Blob} blob - File data as blob
     * @param {string} filename - Name for downloaded file
     */
    function downloadFile(blob, filename) {
        // Create temporary URL for blob
        const downloadUrl = window.URL.createObjectURL(blob);

        // Create hidden anchor element
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);

        // Trigger download
        a.click();

        // Cleanup
        setTimeout(() => {
            window.URL.revokeObjectURL(downloadUrl);
            document.body.removeChild(a);
        }, 100);
    }

    // ==================== PUBLIC API ====================

    /**
     * Public methods exposed by the module
     */
    return {
        init: init,
        exportUnits: exportUnits
    };
})();

// ==================== MODULE INITIALIZATION ====================

/**
 * Initialize DataManager when DOM is ready
 * Ensures all elements are loaded before setup
 */
document.addEventListener('DOMContentLoaded', DataManager.init);