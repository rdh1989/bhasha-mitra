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

            this.jobId = jobElement.value;

            this.startPolling();

        }

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

            /*
            const response =
                await Api.get(
                    `/api/translations/${this.jobId}/status`
                );

            this.updateStatus(response);
            */

            this.simulateProgress();

        }
        catch (error) {

            console.error(error);

            this.stopPolling();

        }

    }

    /*=========================================================================
        Update UI
    =========================================================================*/

    updateStatus(data) {

        this.setProgress(data.progress);

        this.setStage(data.stage);

        this.setStatus(data.status);

        if (data.status === "Completed") {

            this.stopPolling();

            App.showToast("Translation Completed");

        }

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

    /*=========================================================================
        Demo Mode
    =========================================================================*/

    simulateProgress() {

        if (!this.progressBar)
            return;

        let progress = parseInt(

            this.progressValue?.textContent || "0"

        );

        if (progress >= 100) {

            this.setStatus("Completed");

            this.setStage("Finished");

            this.stopPolling();

            return;

        }

        progress += 5;

        const stages = [

            "Extracting Audio",

            "Speech Recognition",

            "Language Translation",

            "Voice Synthesis",

            "Rendering Video",

            "Finalizing"

        ];

        const stageIndex = Math.min(

            Math.floor(progress / 20),

            stages.length - 1

        );

        this.setProgress(progress);

        this.setStage(

            stages[stageIndex]

        );

        this.setStatus("Running");

    }

}

document.addEventListener(

    "DOMContentLoaded",

    () => {

        window.Translation = new TranslationController();

    }

);