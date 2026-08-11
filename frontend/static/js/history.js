/******************************************************************************
 *
 * Bhasha Mitra
 * History Controller
 *
 * Description:
 * Handles Translation History
 *
 * Author  : Team 4
 * Version : 1.0.0
 *
 *****************************************************************************/

class HistoryController {

    constructor() {

        this.tableBody = document.getElementById("historyTableBody");

        this.searchBox = document.getElementById("historySearch");

        this.statusFilter = document.getElementById("statusFilter");

        this.refreshButton = document.getElementById("refreshHistory");

        this.detailsModal = document.getElementById("translationDetailsModal");

        this.detailsBody = document.getElementById("translationDetailsBody");

        this.closeDetailsModalButton = document.getElementById("closeDetailsModal");

        this.ensureDetailsModal();

        this.currentPage = 1;

        this.pageSize = 10;

        this.history = [];

        this.initialize();

    }

    static openDetailsFromButton(button) {

        if (!(button instanceof HTMLElement)) {

            return;

        }

        const id = button.dataset.id;

        if (window.History && typeof window.History.showDetails === "function") {

            window.History.showDetails(id);

        }

    }

    /*=========================================================================
        Initialize
    =========================================================================*/

    async initialize() {

        this.registerEvents();

        await this.loadHistory();

    }

    /*=========================================================================
        Events
    =========================================================================*/

    registerEvents() {

        this.searchBox?.addEventListener(

            "input",

            () => this.filterHistory()

        );

        this.statusFilter?.addEventListener(

            "change",

            () => this.filterHistory()

        );

        this.refreshButton?.addEventListener(

            "click",

            () => this.loadHistory()

        );

        this.tableBody?.addEventListener(

            "click",

            (event) => {

                const target = event.target;

                if (!(target instanceof Element)) {

                    return;

                }

                const detailsButton = target.closest(".btn-details");

                if (detailsButton instanceof HTMLElement) {

                    this.showDetails(detailsButton.dataset.id);

                    return;

                }

                const legacyViewButton = target.closest(".action-btn.view");

                if (legacyViewButton instanceof HTMLElement) {

                    this.showDetails(legacyViewButton.dataset.id);

                    return;

                }

                const legacyDownloadButton = target.closest(".action-btn.download");

                if (legacyDownloadButton instanceof HTMLElement) {

                    this.showDetails(legacyDownloadButton.dataset.id);

                    return;

                }

                const deleteButton = target.closest(".btn-delete");

                if (deleteButton instanceof HTMLElement) {

                    this.delete(deleteButton.dataset.id);

                }

            }

        );

        document.addEventListener(

            "click",

            (event) => {

                const target = event.target;

                if (!(target instanceof Element)) {

                    return;

                }

                const detailsButton = target.closest(".btn-details, .action-btn.view, .action-btn.download");

                if (detailsButton instanceof HTMLElement) {

                    event.preventDefault();
                    this.showDetails(detailsButton.dataset.id);
                    return;

                }

                const deleteButton = target.closest(".btn-delete, .action-btn.delete");

                if (deleteButton instanceof HTMLElement) {

                    event.preventDefault();
                    this.delete(deleteButton.dataset.id);

                }

            }

        );

        this.closeDetailsModalButton?.addEventListener(

            "click",

            () => this.closeDetailsModal()

        );

        this.detailsModal?.addEventListener(

            "click",

            (event) => {

                const target = event.target;

                if (target instanceof HTMLElement && target.dataset.close === "details-modal") {

                    this.closeDetailsModal();

                }

            }

        );

        document.addEventListener(

            "keydown",

            (event) => {

                if (event.key === "Escape") {

                    this.closeDetailsModal();

                }

            }

        );

    }

    /*=========================================================================
        Load History
    =========================================================================*/

    async loadHistory() {

        try {

            App.showLoading("Loading History...");

            const response = await fetch(
                "/api/v1/translations",
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
                    "Unable to load translation history."
                );

            }

            this.history = payload.translations.map(record => ({
                id: record.job_id,
                fileName: record.file_name,
                inputFile: record.input_file || "--",
                sourceLanguage: record.source_language || "auto",
                targetLanguage: record.target_language || "-",
                createdAt: this.formatDate(record.created_at),
                duration: "--",
                status: this.formatStatus(record.status),
                statusRaw: record.status || "PENDING",
                stage: record.display_stage || "Pending",
                errorMessage: record.error_message || ""
            }));

            this.render(this.history);

        }
        catch (error) {

            console.error(error);

            App.showToast(

                "Unable to load history",

                "error"

            );

        }
        finally {

            App.hideLoading();

        }

    }

    /*=========================================================================
        Render Table
    =========================================================================*/

    render(records) {

        if (!this.tableBody)
            return;

        this.tableBody.innerHTML = "";

        if (records.length === 0) {

            this.tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center">
                        No Records Found
                    </td>
                </tr>
            `;

            return;

        }

        records.forEach(record => {

            this.tableBody.insertAdjacentHTML(

                "beforeend",

                `
                <tr>

                    <td>
                        <div class="video-info">
                            <div class="video-icon">
                                <i class="fas fa-video"></i>
                            </div>
                            <div>
                                <div class="video-name">${record.fileName}</div>
                            </div>
                        </div>
                    </td>

                    <td>
                        <div class="language-pair">
                            ${record.sourceLanguage}
                            <i class="fas fa-arrow-right language-arrow"></i>
                            ${record.targetLanguage}
                        </div>
                    </td>

                    <td>${record.createdAt}</td>

                    <td>${record.duration}</td>

                    <td>
                        <span class="status ${record.status.toLowerCase().replace(/\s+/g, "-")}">
                            <span class="status-dot"></span>
                            ${record.status}
                        </span>
                    </td>

                    <td>

                        <button
                            type="button"
                            class="action-btn details btn-details"
                            onclick="HistoryController.openDetailsFromButton(this)"
                            data-id="${record.id}">

                            Details

                        </button>

                        <button
                            type="button"
                            class="btn btn-danger btn-delete"
                            onclick="window.History && window.History.delete(this.dataset.id)"
                            data-id="${record.id}">

                            <i class="fa-solid fa-trash"></i>

                        </button>

                    </td>

                </tr>
                `

            );

        });

        this.registerRowEvents();

    }

    ensureDetailsModal() {

        if (this.detailsModal && this.detailsBody && this.closeDetailsModalButton) {

            // Keep modal outside page flow so it behaves like a real popup.
            if (this.detailsModal.parentElement !== document.body) {

                document.body.appendChild(this.detailsModal);

            }

            return;

        }

        const wrapper = document.createElement("div");
        wrapper.innerHTML = `
            <div id="translationDetailsModal" class="details-modal" aria-hidden="true">
                <div class="details-modal-backdrop" data-close="details-modal"></div>
                <div class="details-modal-dialog" role="dialog" aria-modal="true" aria-labelledby="detailsModalTitle">
                    <div class="details-modal-header">
                        <h3 id="detailsModalTitle">Translation Job Details</h3>
                        <button type="button" class="details-close" id="closeDetailsModal" aria-label="Close details">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="details-modal-body" id="translationDetailsBody">
                        <p class="details-loading">Loading details...</p>
                    </div>
                </div>
            </div>
        `;

        const modal = wrapper.firstElementChild;

        if (modal) {

            document.body.appendChild(modal);

            this.detailsModal = document.getElementById("translationDetailsModal");
            this.detailsBody = document.getElementById("translationDetailsBody");
            this.closeDetailsModalButton = document.getElementById("closeDetailsModal");

        }

    }

    /*=========================================================================
        Search + Filter
    =========================================================================*/

    filterHistory() {

        const keyword =

            this.searchBox?.value.toLowerCase() || "";

        const status =

            this.statusFilter?.value || "";

        let filtered = this.history.filter(item => {

            const matchesSearch =

                item.fileName.toLowerCase().includes(keyword);

            const matchesStatus =

                status === "" ||

                item.status.toLowerCase() === status.toLowerCase();

            return matchesSearch && matchesStatus;

        });

        this.render(filtered);

    }

    formatStatus(status) {

        return (status || "PENDING")
            .toLowerCase()
            .replace(/_/g, " ")
            .replace(/\b\w/g, letter => letter.toUpperCase());

    }

    formatDate(value) {

        if (!value) {

            return "--";

        }

        const date = new Date(value);

        if (Number.isNaN(date.getTime())) {

            return value;

        }

        return date.toLocaleString();

    }

    /*=========================================================================
        Row Buttons
    =========================================================================*/

    registerRowEvents() {

        // Kept for backward compatibility; click handling is delegated in registerEvents().

    }

    /*=========================================================================
        Details
    =========================================================================*/

    openDetailsModal() {

        if (!this.detailsModal) {

            return;

        }

        this.detailsModal.classList.add("is-open");

        this.detailsModal.setAttribute("aria-hidden", "false");

    }

    closeDetailsModal() {

        if (!this.detailsModal) {

            return;

        }

        this.detailsModal.classList.remove("is-open");

        this.detailsModal.setAttribute("aria-hidden", "true");

    }

    async showDetails(id) {

        if (!this.detailsBody) {

            return;

        }

        if (!id) {

            this.detailsBody.innerHTML = `
                <div class="details-error">
                    <div class="details-error-title">Unable to open details</div>
                    <p>Job id is missing for this record.</p>
                </div>
            `;

            this.openDetailsModal();

            return;

        }

        this.detailsBody.innerHTML = `
            <p class="details-loading">Loading details...</p>
        `;

        this.openDetailsModal();

        try {

            const response = await fetch(
                `/api/v1/jobs/${encodeURIComponent(id)}`,
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
                    "Unable to load translation details."
                );

            }

            const job = payload.job;

            const sourceLanguage = job.source_language || "auto";
            const targetLanguage = job.target_language || "-";
            const stageStatus = job.display_stage || "Pending";
            const status = this.formatStatus(job.status);
            const inputVideo = this.extractFileName(job.input_file);
            const errorMessage = (job.error_message || "").trim();
            const stageTimeline = this.buildStageTimeline(job);
            const timelineHtml = stageTimeline.map(stage => `
                <div class="stage-row">
                    <span class="stage-name">${this.escapeHtml(stage.name)}</span>
                    <span class="stage-state ${this.stageStateClass(stage.state)}">${this.escapeHtml(stage.state)}</span>
                </div>
            `).join("");

            this.detailsBody.innerHTML = `
                <div class="details-grid">
                    <div class="details-item">
                        <span class="details-label">Job ID</span>
                        <span class="details-value">${this.escapeHtml(job.job_id || id)}</span>
                    </div>

                    <div class="details-item">
                        <span class="details-label">Input Video</span>
                        <span class="details-value">${this.escapeHtml(inputVideo)}</span>
                    </div>

                    <div class="details-item">
                        <span class="details-label">Status</span>
                        <span class="details-value">${this.escapeHtml(status)}</span>
                    </div>

                    <div class="details-item">
                        <span class="details-label">Stage Status</span>
                        <span class="details-value">${this.escapeHtml(stageStatus)}</span>
                    </div>

                    <div class="details-item">
                        <span class="details-label">Language Pair</span>
                        <span class="details-value">${this.escapeHtml(sourceLanguage)} → ${this.escapeHtml(targetLanguage)}</span>
                    </div>

                    <div class="details-item">
                        <span class="details-label">Created At</span>
                        <span class="details-value">${this.escapeHtml(this.formatDate(job.created_at))}</span>
                    </div>
                </div>

                <div class="stage-breakdown">
                    <div class="stage-breakdown-title">Pipeline Stages</div>
                    <div class="stage-timeline">
                        ${timelineHtml}
                    </div>
                </div>

                ${errorMessage ? `
                    <div class="details-error">
                        <div class="details-error-title">Failure Reason</div>
                        <p>${this.escapeHtml(errorMessage)}</p>
                    </div>
                ` : ""}
            `;

        }
        catch (error) {

            console.error(error);

            this.detailsBody.innerHTML = `
                <div class="details-error">
                    <div class="details-error-title">Unable to load details</div>
                    <p>${this.escapeHtml(error?.message || "Unknown error")}</p>
                </div>
            `;

        }

    }

    extractFileName(pathValue) {

        if (!pathValue) {

            return "--";

        }

        const normalized = String(pathValue).replace(/\\/g, "/");
        const parts = normalized.split("/");
        const last = parts[parts.length - 1];

        return last || normalized;

    }

    escapeHtml(value) {

        const text = String(value ?? "");

        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#39;");

    }

    stageStateClass(state) {

        const normalized = String(state || "")
            .toLowerCase()
            .replace(/\s+/g, "-");

        if (normalized.includes("completed")) {
            return "is-completed";
        }

        if (normalized.includes("progress") || normalized.includes("running")) {
            return "is-running";
        }

        if (normalized.includes("failed")) {
            return "is-failed";
        }

        if (normalized.includes("queued")) {
            return "is-queued";
        }

        return "is-pending";

    }

    buildStageTimeline(job) {

        const status = String(job?.status || "PENDING").toUpperCase();
        const displayStage = String(job?.display_stage || "").toLowerCase();
        const errorMessage = String(job?.error_message || "").toLowerCase();
        const preprocessing = job?.preprocessing || {};

        const timeline = [
            { name: "Transcript Generation", state: "Pending" },
            { name: "Translation", state: "Pending" },
            { name: "Text to Speech", state: "Pending" },
            { name: "Dubbing Video Generation", state: "Pending" },
        ];

        // Transcript stage
        if (preprocessing.asr_completed) {
            timeline[0].state = "Completed";
        } else if (preprocessing.audio_extracted) {
            timeline[0].state = "In Progress";
        }

        // Translation stage
        if (status === "QUEUED") {
            timeline[1].state = "Queued";
        } else if (status === "RUNNING") {
            timeline[1].state = "In Progress";
        }

        if (preprocessing.asr_completed && ["COMPLETED", "FAILED", "CANCELLED"].includes(status)) {
            timeline[1].state = "Completed";
        }

        if (status === "FAILED" && displayStage.includes("translation")) {
            timeline[1].state = "Failed";
        }

        const dubbingFailure = (
            status === "FAILED"
            && (
                errorMessage.includes("dubbing")
                || errorMessage.includes("text to speech")
                || errorMessage.includes("tts")
                || errorMessage.includes("overlapping timestamps")
            )
        );

        // Text to speech + dubbing stage
        if (status === "COMPLETED") {
            timeline[2].state = "Completed";
            timeline[3].state = "Completed";
        }

        if (dubbingFailure) {
            timeline[2].state = "Failed";
            timeline[3].state = "Failed";
        }

        return timeline;

    }

    /*=========================================================================
        Delete
    =========================================================================*/

    async delete(id) {

        if (!confirm(

            "Delete this translation?"

        ))
            return;

        try {

            /*
            await Api.delete(
                `/api/history/${id}`
            );
            */

            this.history = this.history.filter(

                item => item.id != id

            );

            this.render(this.history);

            App.showToast(

                "History Deleted"

            );

        }
        catch (error) {

            console.error(error);

            App.showToast(

                "Delete Failed",

                "error"

            );

        }

    }

    /*=========================================================================
        Demo
    =========================================================================*/

    demoData() {

        return [

            {

                id:1,

                file:"Meeting.mp4",

                source:"English",

                target:"Marathi",

                date:"21-Jul-2026",

                duration:"08:25",

                status:"Completed"

            },

            {

                id:2,

                file:"Training.mp4",

                source:"Hindi",

                target:"Tamil",

                date:"20-Jul-2026",

                duration:"15:12",

                status:"Completed"

            },

            {

                id:3,

                file:"Lecture.mp4",

                source:"English",

                target:"Gujarati",

                date:"18-Jul-2026",

                duration:"42:10",

                status:"Completed"

            }

        ];

    }

}

document.addEventListener(

    "DOMContentLoaded",

    () => {

        window.History =

            new HistoryController();

    }

);