/* Shared job-table rendering + polling helpers used by the dashboard and history pages. */

const STAGE_META = {
  queued: { label: "Queued", cls: "status-queued" },
  cancelling: { label: "Cancelling", cls: "status-running" },
  extracting_audio: { label: "Preparing audio", cls: "status-running" },
  transcribing: { label: "Understanding speech", cls: "status-running" },
  translating: { label: "Translating speech", cls: "status-running" },
  synthesizing_speech: { label: "Generating dubbed speech", cls: "status-running" },
  processing_onscreen_text: { label: "Translating on-screen text", cls: "status-running" },
  muxing_video: { label: "Finalizing video", cls: "status-running" },
  completed: { label: "Completed", cls: "status-completed" },
  failed: { label: "Failed", cls: "status-failed" },
  cancelled: { label: "Cancelled", cls: "status-failed" },
};

function stageMeta(stage) {
  return STAGE_META[stage] || { label: stage, cls: "status-queued" };
}

function languageLabel(code) {
  const map = window.__LANGUAGE_LABELS__ || {};
  return map[code] || code;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function formatDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

function formatDuration(seconds) {
  if (seconds == null) return "-";
  const total = Math.round(seconds);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function formatElapsed(createdAt, endedAt = null) {
  if (!createdAt) return "";
  const start = new Date(createdAt).getTime();
  const end = endedAt ? new Date(endedAt).getTime() : Date.now();
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) return "";
  return formatDuration((end - start) / 1000);
}

function showNotification(message, kind = "info") {
  const region = document.getElementById("notification-region");
  if (!region) return;
  region.textContent = "";
  const item = document.createElement("div");
  const messageEl = document.createElement("span");
  const close = document.createElement("button");
  item.className = `notification notification-${kind}`;
  item.setAttribute("role", kind === "error" ? "alert" : "status");
  messageEl.className = "notification-message";
  messageEl.textContent = message;
  close.type = "button";
  close.className = "notification-close";
  close.setAttribute("aria-label", "Dismiss notification");
  close.textContent = "×";
  close.addEventListener("click", () => item.remove());
  item.append(messageEl, close);
  region.appendChild(item);
  if (kind !== "error") {
    window.setTimeout(() => item.remove(), 5000);
  }
}

const knownJobStages = new Map();
const completionNotifications = new Set();

function handleUnauthorizedResponse(response) {
  if (response.status !== 401) return response;
  window.__stopProtectedPolling?.();
  if (!window.__authRedirecting) {
    window.__authRedirecting = true;
    window.location.replace("/login");
  }
  const error = new Error("Your session has expired. Please sign in again.");
  error.code = "AUTH_REQUIRED";
  throw error;
}

async function fetchJobs({ limit = 20, offset = 0, status = "" } = {}) {
  const params = new URLSearchParams({ limit, offset });
  if (status) params.set("status", status);
  const res = await fetch(`/api/jobs?${params.toString()}`);
  handleUnauthorizedResponse(res);
  if (!res.ok) throw new Error(`Failed to load jobs (${res.status})`);
  return res.json();
}

async function fetchStats() {
  const res = await fetch("/api/stats");
  handleUnauthorizedResponse(res);
  if (!res.ok) throw new Error("Failed to load stats");
  return res.json();
}

function jobRowHtml(job, { allowDelete = false, allowDetails = false, allowRetry = false } = {}) {
  const meta = stageMeta(job.stage);
  const pct = Math.round((job.progress || 0) * 100);
  const jobId = escapeHtml(job.id);
  const filename = escapeHtml(job.filename || "video");
  const elapsed = formatElapsed(job.created_at, job.ended_at);
  const timeTaken = job.done
    ? formatDuration(job.duration_seconds)
    : (elapsed ? `Elapsed ${elapsed}` : "-");
  const actions = [];
  if (allowDetails) {
    actions.push(`<button class="link-btn" data-details-job="${jobId}" aria-label="View details for ${filename}">Details</button>`);
  }
  if (job.stage === "completed" && job.has_output) {
    actions.push(`<a href="/media/output/${jobId}" class="link" download aria-label="Download ${filename}">Download</a>`);
  }
  if (job.error) {
    actions.push(`<span class="error-inline" title="${escapeHtml(job.error)}">${escapeHtml(job.error)}</span>`);
  }
  if (allowRetry && (job.stage === "failed" || job.stage === "cancelled")) {
    actions.push(`<button class="link-btn" data-retry-job="${jobId}" aria-label="Retry ${filename}">Retry</button>`);
  }
  if (allowRetry && !job.done && job.stage !== "cancelling") {
    actions.push(`<button class="link-btn danger" data-cancel-job="${jobId}" aria-label="Cancel ${filename}">Cancel</button>`);
  }
  if (allowDelete) {
    actions.push(`<button class="link-btn danger" data-delete-job="${jobId}" aria-label="Delete ${filename}">Delete</button>`);
  }
  return `
    <tr data-job-row="${jobId}" class="job-row job-row-${meta.cls.replace("status-", "")}">
      <td data-label="Job ID" class="mono ellipsis" title="${jobId}">${escapeHtml(String(job.id).slice(0, 8))}</td>
      <td data-label="Video" class="ellipsis" title="${filename}"><strong>${filename}</strong></td>
      <td data-label="Target">${escapeHtml(languageLabel(job.target_lang))}</td>
      <td data-label="Status"><span class="status-badge ${meta.cls}">${meta.label}</span></td>
      <td data-label="Progress">
        <div class="mini-progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}" aria-label="${escapeHtml(meta.label)} progress"><div class="mini-progress-fill" style="width:${pct}%"></div></div>
        <span class="mini-progress-text">${pct}%${job.done ? "" : formatElapsed(job.created_at) ? ` · ${escapeHtml(formatElapsed(job.created_at))}` : ""}</span>
      </td>
      <td data-label="Submitted by">${escapeHtml(job.username || "-")}</td>
      <td data-label="Created">${formatDate(job.created_at)}</td>
      <td data-label="Ended">${job.ended_at ? formatDate(job.ended_at) : "-"}</td>
      <td data-label="Duration">${escapeHtml(timeTaken)}</td>
      <td class="row-actions">${actions.join(" &middot; ")}</td>
    </tr>`;
}

function renderJobsTable(tbody, jobs, opts = {}) {
  jobs.forEach((job) => {
    const previousStage = knownJobStages.get(job.id);
    if (previousStage && previousStage !== "completed" && job.stage === "completed" && !completionNotifications.has(job.id)) {
      completionNotifications.add(job.id);
      showNotification(`Dubbed video ready: ${job.filename || "video"}`, "success");
    }
    knownJobStages.set(job.id, job.stage);
  });
  if (!jobs.length) {
    tbody.innerHTML = `<tr><td colspan="10" class="empty-cell"><strong>No dubbing jobs yet</strong><span>Start a job from the Dashboard to see progress here.</span></td></tr>`;
    return;
  }
  tbody.innerHTML = jobs.map((job) => jobRowHtml(job, opts)).join("");
}

function bindDeleteButtons(tbody, onDeleted) {
  tbody.addEventListener("click", async (event) => {
    const btn = event.target.closest("[data-delete-job]");
    if (!btn) return;
    const jobId = btn.getAttribute("data-delete-job");
    if (!await (window.confirmAppAction?.("Delete this job and its output permanently?", "Delete job") ?? Promise.resolve(false))) return;
    const res = await fetch(`/api/jobs/${jobId}`, { method: "DELETE" });
    if (res.ok) {
      showNotification("Job deleted.", "success");
      onDeleted?.();
    } else {
      showNotification("The job could not be deleted. Try again.", "error");
    }
  });
}

function bindRetryButtons(tbody, onRetried) {
  tbody.addEventListener("click", async (event) => {
    const btn = event.target.closest("[data-retry-job]");
    if (!btn || btn.disabled) return;
    const jobId = btn.getAttribute("data-retry-job");
    btn.disabled = true;
    try {
      const res = await fetch(`/api/jobs/${jobId}/retry`, { method: "POST" });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || `Retry failed (${res.status})`);
      showNotification("The job has been queued again.", "success");
      onRetried?.();
    } catch (err) {
      showNotification(err.message, "error");
      btn.disabled = false;
    }
  });
}

function bindCancelButtons(tbody, onCancelled) {
  tbody.addEventListener("click", async (event) => {
    const btn = event.target.closest("[data-cancel-job]");
    if (!btn || btn.disabled) return;
    const jobId = btn.getAttribute("data-cancel-job");
    if (!await (window.confirmAppAction?.("Cancel this job? Completed stages will be retained for Retry.", "Cancel job") ?? Promise.resolve(false))) return;
    btn.disabled = true;
    try {
      const res = await fetch(`/api/jobs/${jobId}/cancel`, { method: "POST" });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || `Cancel failed (${res.status})`);
      showNotification("The job is being cancelled.", "success");
      onCancelled?.();
    } catch (err) {
      showNotification(err.message, "error");
      btn.disabled = false;
    }
  });
}

function bindDetailsButtons(tbody, dialogEl) {
  let detailsReturnFocus = null;
  dialogEl.addEventListener("close", () => window.setTimeout(() => detailsReturnFocus?.focus(), 0));
  tbody.addEventListener("click", async (event) => {
    const btn = event.target.closest("[data-details-job]");
    if (!btn) return;
    const jobId = btn.getAttribute("data-details-job");
    detailsReturnFocus = btn;
    const returnFocus = () => btn.focus();
    btn.disabled = true;
    btn.classList.add("is-loading");
    btn.setAttribute("aria-busy", "true");
    const loading = dialogEl.querySelector(".dialog-loading");
    const metaEl = dialogEl.querySelector(".dialog-meta");
    const errorEl = dialogEl.querySelector(".dialog-error");
    const download = dialogEl.querySelector(".dialog-download");
    const logEl = dialogEl.querySelector(".dialog-log");
    const sourcePathEl = dialogEl.querySelector("[data-dialog-source-path]");
    const outputPathEl = dialogEl.querySelector("[data-dialog-output-path]");
    dialogEl.querySelector(".dialog-title").textContent = "Loading job details...";
    metaEl.textContent = "";
    loading.hidden = false;
    errorEl.hidden = true;
    download.hidden = true;
    logEl.textContent = "";
    if (sourcePathEl) sourcePathEl.textContent = "Unavailable in job details";
    if (outputPathEl) outputPathEl.textContent = "Unavailable in job details";
    if (!dialogEl.open) dialogEl.showModal();
    try {
      const res = await fetch(`/api/jobs/${jobId}`);
      if (!res.ok) throw new Error("Job details could not be loaded.");
      const job = await res.json();
      const meta = stageMeta(job.stage);
      const detailRows = [
        ["Job ID", job.id],
        ["Video", job.filename],
        ["Source", job.source_lang ? languageLabel(job.source_lang) : null],
        ["Detected source", job.detected_source_lang],
        ["Target", job.target_lang ? languageLabel(job.target_lang) : null],
        ["Status", meta.label],
        ["Progress", job.progress != null ? `${Math.round(Number(job.progress) * 100)}%` : null],
        ["Current stage", job.stage],
        ["Created", job.created_at ? formatDate(job.created_at) : null],
        ["Started", job.started_at ? formatDate(job.started_at) : null],
        ["Ended", job.ended_at ? formatDate(job.ended_at) : null],
        ["Duration", job.duration_seconds != null ? formatDuration(job.duration_seconds) : null],
      ].filter(([, value]) => value != null && value !== "");
      dialogEl.querySelector(".dialog-title").textContent = job.filename || "Job details";
      metaEl.innerHTML = detailRows.map(([label, value]) => `<div class="dialog-detail-row"><strong>${escapeHtml(label)}</strong><span>${escapeHtml(value)}</span></div>`).join("");
      errorEl.textContent = job.error || "";
      errorEl.hidden = !job.error;
      logEl.textContent = Array.isArray(job.logs) ? job.logs.join("\n") : "";
      if (sourcePathEl) sourcePathEl.textContent = job.source_path || "Unavailable in job details";
      if (outputPathEl) outputPathEl.textContent = job.output_path || "Unavailable in job details";
      if (download) {
        download.hidden = !(job.stage === "completed" && job.output_path);
        download.href = `/media/output/${encodeURIComponent(job.id)}`;
        download.setAttribute("aria-label", `Download ${job.filename || "video"}`);
      }
    } catch (error) {
      loading.hidden = true;
      errorEl.textContent = error.message || "Job details could not be loaded.";
      errorEl.hidden = false;
      showNotification(errorEl.textContent, "error");
    } finally {
      loading.hidden = true;
      btn.disabled = false;
      btn.classList.remove("is-loading");
      btn.removeAttribute("aria-busy");
    }
  });
}
