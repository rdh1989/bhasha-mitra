/* Dashboard page: multi-file job submission + live-refreshing recent jobs table.
   Relies on helpers defined in jobs.js (loaded first). */

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("upload-form");
  const jobsBody = document.getElementById("jobs-table-body");

  if (form) {
    const startBtn = document.getElementById("start-btn");
    const statusEl = document.getElementById("upload-status");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const videoInput = document.getElementById("video");
      const targetLang = document.getElementById("target_lang").value;
      const files = Array.from(videoInput.files || []);
      if (!files.length) {
        statusEl.innerHTML = `<p class="error">Please choose at least one video file before starting.</p>`;
        return;
      }

      startBtn.disabled = true;
      statusEl.innerHTML = `<p class="muted">Uploading ${files.length} file(s)...</p>`;

      const formData = new FormData();
      files.forEach((file) => formData.append("video", file));
      formData.append("target_lang", targetLang);

      try {
        const res = await fetch("/api/jobs", { method: "POST", body: formData });
        const body = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(body.detail || `Upload failed (${res.status})`);
        statusEl.innerHTML = `<p class="success">Queued ${body.job_ids.length} job(s). Track progress below.</p>`;
        form.reset();
        refreshJobsTable();
      } catch (err) {
        statusEl.innerHTML = `<p class="error">${err.message}</p>`;
      } finally {
        startBtn.disabled = false;
      }
    });
  }

  async function refreshJobsTable() {
    if (!jobsBody) return;
    try {
      const { items } = await fetchJobs({ limit: 8 });
      renderJobsTable(jobsBody, items);
    } catch (err) {
      jobsBody.innerHTML = `<tr><td colspan="7" class="error">${err.message}</td></tr>`;
    }
  }

  async function refreshStats() {
    const els = {
      total: document.getElementById("stat-total"),
      running: document.getElementById("stat-running"),
      completed: document.getElementById("stat-completed"),
      failed: document.getElementById("stat-failed"),
    };
    if (!els.total) return;
    try {
      const stats = await fetchStats();
      els.total.textContent = stats.total;
      els.running.textContent = stats.running;
      els.completed.textContent = stats.completed;
      els.failed.textContent = stats.failed;
    } catch {
      /* keep last known values on transient errors */
    }
  }

  if (jobsBody) {
    refreshJobsTable();
    refreshStats();
    setInterval(refreshJobsTable, 3000);
    setInterval(refreshStats, 5000);
  }
});
