/******************************************************************************
 *
 * Bhasha Mitra
 * Translation Controller
 *
 * Description:
 * Controls translation job lifecycle.
 *
 * Author  : Team 4
 * Version : 1.0.0
 *
 *****************************************************************************/

class TranslationController {

    constructor() {

        this.jobId = null;

        this.statusLabel = document.getElementById("translationStatus");
        this.progressBar = document.getElementById("translationProgressBar");
        this.progressValue = document.getElementById("translationProgressValue");

        this.stageLabel = document.getElementById("currentStage");
        this.submittedJobsList = document.getElementById("submittedJobsList");

        this.downloadVideoButton =
            document.getElementById("downloadVideo");

        this.downloadSubtitleButton =
            document.getElementById("downloadSubtitle");

        this.cancelButton =
            document.getElementById("cancelTranslation");

        this.retryButton =
            document.getElementById("retryTranslation");

        this.pollTimer = null;

        this.initialize();

    }

    /*=========================================================================
        Initialize
    =========================================================================*/

    initialize() {

        this.registerEvents();

        const jobElement = document.getElementById("translationJobId");

        if (jobElement) {

            this.jobId = jobElement.dataset.jobId || null;

            if (this.jobId) {

                this.startPolling();

            }

        }

        this.refreshSubmittedJobs();
        window.addEventListener("storage", () => this.refreshSubmittedJobs());

    }

    /*=========================================================================
        Events
    =========================================================================*/

    registerEvents() {

        this.downloadVideoButton?.addEventListener(

            "click",

            () => this.downloadVideo()

        );

        this.downloadSubtitleButton?.addEventListener(

            "click",

            () => this.downloadSubtitle()

        );

        this.cancelButton?.addEventListener(

            "click",

            () => this.cancelJob()

        );

        this.retryButton?.addEventListener(

            "click",

            () => this.retryJob()

        );

    }

    /*=========================================================================
        Poll Translation Status
    =========================================================================*/

    startPolling() {

        if (!this.jobId)
            return;

        this.pollStatus();

        this.pollTimer = setInterval(() => {

            this.pollStatus();

        }, 3000);

    }

    stopPolling() {

        if (this.pollTimer) {

            clearInterval(this.pollTimer);

            this.pollTimer = null;

        }

    }

    async pollStatus() {

        try {

            const response = await fetch(
                `/api/v1/jobs/${encodeURIComponent(this.jobId)}`,
                {
                    headers: {
                        "Accept": "application/json"
                    }
                }
            );

            const payload = await response.json();

            if (!response.ok || !payload.success) {

                throw new Error(
                    payload.detail ||
                    "Unable to load translation status."
                );

            }

            this.updateStatus(payload.job);

        }
        catch (error) {

            console.error(error);

            this.stopPolling();

        }

    }

    /*=========================================================================
        Submit Jobs UI
    =========================================================================*/

    refreshSubmittedJobs() {

        if (!this.submittedJobsList) {

            return;

        }

        const jobs = this.getStoredJobs();

        if (!jobs.length) {

            this.submittedJobsList.innerHTML = `
                <div class="summary-item">
                    <div class="summary-label">
                        No jobs submitted yet
                    </div>
                </div>
            `;
            return;
        }

        this.submittedJobsList.innerHTML = jobs
            .slice(0, 5)
            .map(job => `
                <div class="summary-item">
                    <div class="summary-label">
                        ${job.jobId || "Unknown job"}
                    </div>
                    <div class="summary-value">
                        ${job.status || "Submitted"}
                    </div>
                </div>
            `)
            .join("");

    }

    getStoredJobs() {

        try {

            const raw = localStorage.getItem("submittedJobs");
            return raw ? JSON.parse(raw) : [];

        } catch {

            return [];

        }

    }

    persistJob(jobId, status = "Submitted") {

        if (!jobId) {

            return;

        }

        const jobs = this.getStoredJobs();
        const existing = jobs.find(item => item.jobId === jobId);

        if (existing) {

            existing.status = status;

        } else {

            jobs.unshift({ jobId, status });
        }

        localStorage.setItem("submittedJobs", JSON.stringify(jobs));
        this.refreshSubmittedJobs();

    }

    /*=========================================================================
        Update UI
    =========================================================================*/

    updateStatus(data) {

        this.setProgress(
            data.display_progress ??
            data.progress?.percentage ??
            0
        );

        this.setStage(
            data.display_stage ||
            data.progress?.stage ||
            "Pending"
        );

        this.setStatus(
            this.formatStatus(data.status)
        );

        this.persistJob(
            data.job_id || this.jobId,
            data.status
        );

        if (["COMPLETED", "FAILED", "CANCELLED"].includes(data.status)) {

            this.stopPolling();

            if (data.status === "COMPLETED") {

                App.showToast("Translation Completed");

            }

        }

    }

    formatStatus(status) {

        if (!status) {

            return "Pending";

        }

        return status
            .toLowerCase()
            .replace(/_/g, " ")
            .replace(/\b\w/g, letter => letter.toUpperCase());

    }

    setStatus(status) {

        if (this.statusLabel) {

            this.statusLabel.textContent = status;

        }

    }

    setStage(stage) {

        if (this.stageLabel) {

            this.stageLabel.textContent = stage;

        }

    }

    setProgress(progress) {

        if (this.progressBar) {

            this.progressBar.style.width = progress + "%";

        }

        if (this.progressValue) {

            this.progressValue.textContent = progress + "%";

        }

    }

    /*=========================================================================
        Cancel
    =========================================================================*/

    async cancelJob() {

        if (!confirm("Cancel translation?"))
            return;

        try {

            /*
            await Api.post(
                `/api/translations/${this.jobId}/cancel`
            );
            */

            this.stopPolling();

            this.setStatus("Cancelled");

            App.showToast("Translation Cancelled");

        }
        catch (error) {

            console.error(error);

            App.showToast(

                "Unable to cancel",

                "error"

            );

        }

    }

    /*=========================================================================
        Retry
    =========================================================================*/

    async retryJob() {

        try {

            /*
            await Api.post(
                `/api/translations/${this.jobId}/retry`
            );
            */

            this.startPolling();

            App.showToast(

                "Translation Restarted"

            );

        }
        catch (error) {

            console.error(error);

        }

    }

    /*=========================================================================
        Download Video
    =========================================================================*/

    async downloadVideo() {

        try {

            /*
            const blob =
                await Api.download(
                    `/api/translations/${this.jobId}/video`
                );
            */

            App.showToast(

                "Download Started"

            );

        }
        catch (error) {

            console.error(error);

        }

    }

    /*=========================================================================
        Download Subtitle
    =========================================================================*/

    async downloadSubtitle() {

        try {

            /*
            const blob =
                await Api.download(
                    `/api/translations/${this.jobId}/subtitle`
                );
            */

            App.showToast(

                "Subtitle Download Started"

            );

        }
        catch (error) {

            console.error(error);

        }

    }

}

document.addEventListener(

    "DOMContentLoaded",

    () => {

        window.Translation = new TranslationController();

        const jobId = document.getElementById("translationJobId")?.dataset.jobId;

        if (jobId) {

            window.Translation.persistJob(jobId, "PENDING");

        }

    }

);