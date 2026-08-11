/*
===============================================================================
BHASHA MITRA

Module:
    upload.js

Layer:
    Frontend

Description:
    Controls local video selection and translation job creation.

IMPORTANT:
    - Video is NOT uploaded.
    - No FormData is used.
    - No video bytes are sent to the backend.
    - Browse Files calls the local Bhasha Mitra backend.
    - The backend opens the native Windows file picker.
    - Only file_path and file_name are returned to the browser.
    - /api/v1/upload receives JSON containing the local path.
===============================================================================
*/

class UploadController {

    constructor() {

        // =====================================================================
        // Elements
        // =====================================================================

        this.browseButton =
            document.getElementById("browseVideo");

        this.pathInput =
            document.getElementById("videoPath");

        this.startButton =
            document.getElementById("startTranslation");

        this.removeButton =
            document.getElementById("removeFile");

        this.selectedFilePanel =
            document.getElementById("selectedFile");

        this.selectedFileNameElement =
            document.getElementById("selectedFileName");

        this.selectedFileMeta =
            document.getElementById("selectedFileMeta");

        this.sourceLanguage =
            document.getElementById("sourceLanguage");

        this.targetLanguage =
            document.getElementById("targetLanguage");

        this.message =
            document.getElementById("formMessage");

        this.progressContainer =
            document.getElementById("uploadProgress");

        this.progressBar =
            document.getElementById("progressBar");

        this.progressText =
            document.getElementById("progressText");

        this.progressLabel =
            document.getElementById("progressLabel");

        // =====================================================================
        // State
        // =====================================================================

        this.selectedPath = null;

        this.selectedFileName = null;

        // =====================================================================
        // Initialize
        // =====================================================================

        this.initialize();
    }


    // =========================================================================
    // Initialization
    // =========================================================================

    initialize() {

        // ---------------------------------------------------------------------
        // Browse Files
        // ---------------------------------------------------------------------

        if (this.browseButton) {

            this.browseButton.addEventListener(
                "click",
                () => this.browseForVideo()
            );
        }

        // ---------------------------------------------------------------------
        // Manual path
        // ---------------------------------------------------------------------

        if (this.pathInput) {

            this.pathInput.addEventListener(
                "input",
                () => this.handleManualPath()
            );
        }

        // ---------------------------------------------------------------------
        // Remove selected file
        // ---------------------------------------------------------------------

        if (this.removeButton) {

            this.removeButton.addEventListener(
                "click",
                () => this.clearFile()
            );
        }

        // ---------------------------------------------------------------------
        // Start translation
        // ---------------------------------------------------------------------

        if (this.startButton) {

            this.startButton.addEventListener(
                "click",
                () => this.startTranslation()
            );
        }

        // ---------------------------------------------------------------------
        // Target language
        // ---------------------------------------------------------------------

        if (this.targetLanguage) {

            this.targetLanguage.addEventListener(
                "change",
                () => this.updateStartButton()
            );
        }

        // ---------------------------------------------------------------------
        // Source language
        // ---------------------------------------------------------------------

        if (this.sourceLanguage) {

            this.sourceLanguage.addEventListener(
                "change",
                () => this.updateStartButton()
            );
        }

        // ---------------------------------------------------------------------
        // Initial state
        // ---------------------------------------------------------------------

        this.updateStartButton();
    }


    // =========================================================================
    // Browse for local video
    // =========================================================================

    async browseForVideo() {

        if (!this.browseButton) {
            return;
        }

        this.browseButton.disabled = true;

        this.setMessage(
            "Opening file browser..."
        );

        try {

            const response = await fetch(
                "/api/v1/upload/browse",
                {
                    method: "GET",
                    headers: {
                        "Accept": "application/json"
                    }
                }
            );


            // -----------------------------------------------------------------
            // HTTP error
            // -----------------------------------------------------------------

            if (!response.ok) {

                let message =
                    "Unable to open the file browser.";

                try {

                    const error =
                        await response.json();

                    if (
                        typeof error.detail ===
                        "string"
                    ) {

                        message =
                            error.detail;
                    }

                } catch {
                    // Response was not JSON.
                }

                throw new Error(
                    message
                );
            }


            // -----------------------------------------------------------------
            // Parse response
            // -----------------------------------------------------------------

            const result =
                await response.json();


            // -----------------------------------------------------------------
            // User cancelled
            // -----------------------------------------------------------------

            if (
                result.cancelled === true
            ) {

                this.setMessage(
                    "No video selected."
                );

                return;
            }


            // -----------------------------------------------------------------
            // Validate response
            // -----------------------------------------------------------------

            if (
                !result.file_path
            ) {

                throw new Error(
                    "The selected video path was not returned."
                );
            }


            // -----------------------------------------------------------------
            // Set selected file
            // -----------------------------------------------------------------

            this.setSelectedFile(
                result.file_path,
                result.file_name
            );


            this.setMessage(
                "Video selected. Your video will remain on this device.",
                "success"
            );

        } catch (error) {

            console.error(
                "Local video selection failed:",
                error
            );

            this.setMessage(
                error.message ||
                "Unable to select the video.",
                "error"
            );

        } finally {

            this.browseButton.disabled =
                false;
        }
    }


    // =========================================================================
    // Manual path input
    // =========================================================================

    handleManualPath() {

        if (!this.pathInput) {
            return;
        }

        const path =
            this.pathInput.value.trim();


        // ---------------------------------------------------------------------
        // Empty path
        // ---------------------------------------------------------------------

        if (!path) {

            this.clearSelection(
                false
            );

            return;
        }


        // ---------------------------------------------------------------------
        // Extract filename
        // ---------------------------------------------------------------------

        const fileName =
            this.extractFileName(
                path
            );


        if (!fileName) {

            this.setMessage(
                "Enter a valid local video path.",
                "error"
            );

            this.clearSelection(
                false
            );

            return;
        }


        // ---------------------------------------------------------------------
        // Validate extension
        // ---------------------------------------------------------------------

        if (
            !this.validateExtension(
                fileName
            )
        ) {

            this.setMessage(
                "Supported formats are MP4, MOV, AVI, MKV and WEBM.",
                "error"
            );

            this.clearSelection(
                false
            );

            return;
        }


        // ---------------------------------------------------------------------
        // Set selected file
        // ---------------------------------------------------------------------

        this.setSelectedFile(
            path,
            fileName
        );


        this.setMessage(
            "Local video selected.",
            "success"
        );
    }


    // =========================================================================
    // Set selected file
    // =========================================================================

    setSelectedFile(
        filePath,
        fileName
    ) {

        if (!filePath) {
            return;
        }


        this.selectedPath =
            filePath;


        this.selectedFileName =
            fileName ||
            this.extractFileName(
                filePath
            );


        // ---------------------------------------------------------------------
        // Display path
        // ---------------------------------------------------------------------

        if (this.pathInput) {

            this.pathInput.value =
                this.selectedPath;
        }


        // ---------------------------------------------------------------------
        // Display filename
        // ---------------------------------------------------------------------

        if (
            this.selectedFileNameElement
        ) {

            this.selectedFileNameElement.textContent =
                this.selectedFileName;
        }


        // ---------------------------------------------------------------------
        // Display metadata
        // ---------------------------------------------------------------------

        if (this.selectedFileMeta) {

            this.selectedFileMeta.textContent =
                "Local file · Ready for translation";
        }


        // ---------------------------------------------------------------------
        // Show selected file panel
        // ---------------------------------------------------------------------

        if (this.selectedFilePanel) {

            this.selectedFilePanel.hidden =
                false;
        }


        // ---------------------------------------------------------------------
        // Enable start button
        // ---------------------------------------------------------------------

        this.updateStartButton();
    }


    // =========================================================================
    // Extract filename from Windows path
    // =========================================================================

    extractFileName(
        filePath
    ) {

        if (!filePath) {
            return "";
        }


        const normalizedPath =
            filePath.replaceAll(
                "\\",
                "/"
            );


        const parts =
            normalizedPath.split(
                "/"
            );


        return (
            parts[
                parts.length - 1
            ] || ""
        );
    }


    // =========================================================================
    // Validate video extension
    // =========================================================================

    validateExtension(
        fileName
    ) {

        if (!fileName) {
            return false;
        }


        const allowedExtensions = [
            ".mp4",
            ".mov",
            ".avi",
            ".mkv",
            ".webm"
        ];


        const lastDot =
            fileName.lastIndexOf(
                "."
            );


        if (lastDot === -1) {
            return false;
        }


        const extension =
            fileName
                .substring(
                    lastDot
                )
                .toLowerCase();


        return allowedExtensions.includes(
            extension
        );
    }


    // =========================================================================
    // Update Start Translation button
    // =========================================================================

    updateStartButton() {

        if (!this.startButton) {
            return;
        }


        const hasVideo =
            Boolean(
                this.selectedPath
            );


        const hasTargetLanguage =
            Boolean(
                this.targetLanguage &&
                this.targetLanguage.value
            );


        this.startButton.disabled =
            !hasVideo ||
            !hasTargetLanguage;
    }


    // =========================================================================
    // Start translation
    // =========================================================================

    async startTranslation() {

        // ---------------------------------------------------------------------
        // Validate video
        // ---------------------------------------------------------------------

        if (!this.selectedPath) {

            this.setMessage(
                "Select a video before starting translation.",
                "error"
            );

            return;
        }


        // ---------------------------------------------------------------------
        // Validate target language
        // ---------------------------------------------------------------------

        const targetLanguage =
            this.targetLanguage
                ?.value;


        if (!targetLanguage) {

            this.setMessage(
                "Select a target language.",
                "error"
            );

            return;
        }


        // ---------------------------------------------------------------------
        // Source language
        // ---------------------------------------------------------------------

        const sourceLanguage =
            this.sourceLanguage
                ?.value ||
            "auto";


        // ---------------------------------------------------------------------
        // Disable button
        // ---------------------------------------------------------------------

        if (this.startButton) {

            this.startButton.disabled =
                true;
        }


        // ---------------------------------------------------------------------
        // Show progress
        // ---------------------------------------------------------------------

        if (this.progressContainer) {

            this.progressContainer.hidden =
                false;
        }


        this.setProgressLabel(
            "Creating translation job"
        );


        this.updateProgress(
            10
        );


        this.setMessage(
            "Creating translation job. The video is not being uploaded."
        );


        try {

            // =================================================================
            // Request payload
            //
            // IMPORTANT:
            // Only metadata/path is sent.
            // No video bytes.
            // No FormData.
            // =================================================================

            const payload = {

                file_path:
                    this.selectedPath,

                file_name:
                    this.selectedFileName,

                source_language:
                    sourceLanguage,

                target_language:
                    targetLanguage
            };


            console.info(
                "Creating translation job:",
                {
                    file_path:
                        payload.file_path,

                    file_name:
                        payload.file_name,

                    source_language:
                        payload.source_language,

                    target_language:
                        payload.target_language
                }
            );


            // =================================================================
            // Call backend
            // =================================================================

            const response =
                await fetch(
                    "/api/v1/upload",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json",

                            "Accept":
                                "application/json"
                        },

                        body:
                            JSON.stringify(
                                payload
                            )
                    }
                );


            // =================================================================
            // Parse response
            // =================================================================

            const result =
                await this.parseResponse(
                    response
                );


            // =================================================================
            // Success
            // =================================================================

            this.updateProgress(
                100
            );


            this.setProgressLabel(
                "Translation job created"
            );


            this.setMessage(
                `Translation job created successfully. Job ID: ${result.job_id}`,
                "success"
            );

            if (result.job_id) {

                this.persistSubmittedJob(
                    result.job_id,
                    {
                        fileName: payload.file_name,
                        sourceLanguage: payload.source_language,
                        targetLanguage: payload.target_language,
                        status: "PENDING"
                    }
                );

                window.location.href =
                    `/translation?job_id=${encodeURIComponent(result.job_id)}&source_language=${encodeURIComponent(payload.source_language)}&target_language=${encodeURIComponent(payload.target_language)}`;

                return;
            }

            console.info(
                "Translation job created:",
                result
            );

        } catch (error) {

            console.error(
                "Translation job creation failed:",
                error
            );


            this.updateProgress(
                0
            );


            this.setProgressLabel(
                "Unable to create translation job"
            );


            this.setMessage(
                error.message ||
                "Unable to create translation job.",
                "error"
            );

        } finally {

            this.updateStartButton();
        }
    }


    // =========================================================================
    // Local job storage
    // =========================================================================

    getStoredJobs() {

        try {

            const raw = localStorage.getItem("submittedJobs");
            return raw ? JSON.parse(raw) : [];

        } catch {

            return [];

        }
    }

    persistSubmittedJob(jobId, details = {}) {

        const jobs = this.getStoredJobs().filter(
            job => job.jobId !== jobId
        );

        jobs.unshift({
            jobId,
            fileName: details.fileName || this.selectedFileName,
            sourceLanguage: details.sourceLanguage || this.sourceLanguage?.value || "auto",
            targetLanguage: details.targetLanguage || this.targetLanguage?.value || "",
            status: details.status || "PENDING",
            updatedAt: new Date().toISOString()
        });

        localStorage.setItem(
            "submittedJobs",
            JSON.stringify(jobs)
        );

        window.dispatchEvent(new Event("storage"));
    }

    // =========================================================================
    // Parse backend response
    // =========================================================================

    async parseResponse(
        response
    ) {

        let data;


        // ---------------------------------------------------------------------
        // Parse JSON
        // ---------------------------------------------------------------------

        try {

            data =
                await response.json();

        } catch {

            throw new Error(
                `Server returned HTTP ${response.status}.`
            );
        }


        // ---------------------------------------------------------------------
        // HTTP error
        // ---------------------------------------------------------------------

        if (!response.ok) {

            if (
                typeof data.detail ===
                "string"
            ) {

                throw new Error(
                    data.detail
                );
            }


            if (
                Array.isArray(
                    data.detail
                )
            ) {

                const messages =
                    data.detail
                        .map(
                            item =>
                                item.msg ||
                                "Invalid request."
                        )
                        .join(
                            ", "
                        );


                throw new Error(
                    messages
                );
            }


            throw new Error(
                `Request failed with HTTP ${response.status}.`
            );
        }


        // ---------------------------------------------------------------------
        // Validate successful response
        // ---------------------------------------------------------------------

        if (
            !data ||
            typeof data !== "object"
        ) {

            throw new Error(
                "Server returned an invalid response."
            );
        }


        return data;
    }


    // =========================================================================
    // Remove selected file
    // =========================================================================

    clearFile() {

        this.clearSelection(
            true
        );


        this.setMessage(
            "Select a video to continue."
        );
    }


    // =========================================================================
    // Clear selection
    // =========================================================================

    clearSelection(
        clearPath = true
    ) {

        this.selectedPath =
            null;

        this.selectedFileName =
            null;


        // ---------------------------------------------------------------------
        // Clear input
        // ---------------------------------------------------------------------

        if (
            clearPath &&
            this.pathInput
        ) {

            this.pathInput.value =
                "";
        }


        // ---------------------------------------------------------------------
        // Hide selected file
        // ---------------------------------------------------------------------

        if (
            this.selectedFilePanel
        ) {

            this.selectedFilePanel.hidden =
                true;
        }


        // ---------------------------------------------------------------------
        // Reset progress
        // ---------------------------------------------------------------------

        this.updateProgress(
            0
        );


        // ---------------------------------------------------------------------
        // Update button
        // ---------------------------------------------------------------------

        this.updateStartButton();
    }


    // =========================================================================
    // Progress
    // =========================================================================

    updateProgress(
        value
    ) {

        const numericValue =
            Number(
                value
            );


        const safeValue =
            Math.max(
                0,
                Math.min(
                    100,
                    Number.isFinite(
                        numericValue
                    )
                        ? numericValue
                        : 0
                )
            );


        // ---------------------------------------------------------------------
        // Progress bar
        // ---------------------------------------------------------------------

        if (this.progressBar) {

            this.progressBar.style.width =
                `${safeValue}%`;
        }


        // ---------------------------------------------------------------------
        // Percentage text
        // ---------------------------------------------------------------------

        if (this.progressText) {

            this.progressText.textContent =
                `${safeValue}%`;
        }


        // ---------------------------------------------------------------------
        // Accessibility
        // ---------------------------------------------------------------------

        const progressElement =
            this.progressBar
                ?.parentElement;


        if (progressElement) {

            progressElement.setAttribute(
                "aria-valuenow",
                String(
                    safeValue
                )
            );
        }
    }


    // =========================================================================
    // Progress label
    // =========================================================================

    setProgressLabel(
        message
    ) {

        if (
            this.progressLabel
        ) {

            this.progressLabel.textContent =
                message;
        }
    }


    // =========================================================================
    // Message
    // =========================================================================

    setMessage(
        message,
        type = ""
    ) {

        if (!this.message) {
            return;
        }


        this.message.textContent =
            message;


        this.message.className =
            `form-message${
                type
                    ? ` is-${type}`
                    : ""
            }`;
    }
}


// =============================================================================
// Initialize
// =============================================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        window.Upload =
            new UploadController();

    }
);