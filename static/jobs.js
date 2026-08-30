/* Shared job-table rendering + polling helpers used by the dashboard and history pages. */

const STAGE_META = {
  queued: { label: "Queued", cls: "status-queued" },
  extracting_audio: { label: "Extracting audio", cls: "status-running" },
  transcribing: { label: "Transcribing", cls: "status-running" },
  translating: { label: "Translating", cls: "status-running" },
  synthesizing_speech: { label: "Synthesizing speech", cls: "status-running" },
  muxing_video: { label: "Combining video", cls: "status-running" },
  completed: { label: "Completed", cls: "status-completed" },
  failed: { label: "Failed", cls: "status-failed" },
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

async function fetchJobs({ limit = 20, offset = 0, status = "" } = {}) {
  const params = new URLSearchParams({ limit, offset });
  if (status) params.set("status", status);
  const res = await fetch(`/api/jobs?${params.toString()}`);
  if (!res.ok) throw new Error(`Failed to load jobs (${res.status})`);
  return res.json();
}

async function fetchStats() {
  const res = await fetch("/api/stats");
  if (!res.ok) throw new Error("Failed to load stats");
  return res.json();
}

function jobRowHtml(job, { allowDelete = false, allowDetails = false } = {}) {
  const meta = stageMeta(job.stage);
  const pct = Math.round((job.progress || 0) * 100);
  const actions = [];
  if (allowDetails) {
    actions.push(`<button class="link-btn" data-details-job="${job.id}">Details</button>`);
  }
  if (job.stage === "completed" && job.output_path) {
    actions.push(`<a href="/media/output/${job.id}" class="link" download>Download</a>`);
  }
  if (job.error) {
    actions.push(`<span class="error-inline" title="${escapeHtml(job.error)}">Error</span>`);
  }
  if (allowDelete) {
    actions.push(`<button class="link-btn danger" data-delete-job="${job.id}">Delete</button>`);
  }
  return `
    <tr data-job-row="${job.id}">
      <td class="ellipsis" title="${escapeHtml(job.filename)}">${escapeHtml(job.filename)}</td>
      <td>${escapeHtml(languageLabel(job.target_lang))}</td>
      <td><span class="status-badge ${meta.cls}">${meta.label}</span></td>
      <td>
        <div class="mini-progress"><div class="mini-progress-fill" style="width:${pct}%"></div></div>
        <span class="mini-progress-text">${pct}%</span>
      </td>
      <td>${escapeHtml(job.username || "-")}</td>
      <td>${formatDate(job.created_at)}</td>
      <td class="row-actions">${actions.join(" &middot; ")}</td>
    </tr>`;
}

function renderJobsTable(tbody, jobs, opts = {}) {
  if (!jobs.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="muted">No jobs yet.</td></tr>`;
    return;
  }
  tbody.innerHTML = jobs.map((job) => jobRowHtml(job, opts)).join("");
}

function bindDeleteButtons(tbody, onDeleted) {
  tbody.addEventListener("click", async (event) => {
    const btn = event.target.closest("[data-delete-job]");
    if (!btn) return;
    const jobId = btn.getAttribute("data-delete-job");
    if (!confirm("Delete this job and its output permanently?")) return;
    const res = await fetch(`/api/jobs/${jobId}`, { method: "DELETE" });
    if (res.ok) onDeleted?.();
  });
}

function bindDetailsButtons(tbody, dialogEl) {
  tbody.addEventListener("click", async (event) => {
    const btn = event.target.closest("[data-details-job]");
    if (!btn) return;
    const jobId = btn.getAttribute("data-details-job");
    const res = await fetch(`/api/jobs/${jobId}`);
    if (!res.ok) return;
    const job = await res.json();
    dialogEl.querySelector(".dialog-title").textContent = job.filename;
    dialogEl.querySelector(".dialog-meta").innerHTML = [
      `Target: ${escapeHtml(languageLabel(job.target_lang))}`,
      job.detected_source_lang ? `Detected source: ${escapeHtml(job.detected_source_lang)}` : null,
      `Status: ${stageMeta(job.stage).label}`,
    ].filter(Boolean).join(" &middot; ");
    dialogEl.querySelector(".dialog-log").textContent = (job.logs || []).join("\n");
    dialogEl.querySelector(".dialog-error").textContent = job.error || "";
    dialogEl.querySelector(".dialog-error").hidden = !job.error;
    dialogEl.showModal();
  });
}
