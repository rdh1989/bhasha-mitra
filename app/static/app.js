/* Dashboard page: multi-file job submission + live-refreshing recent jobs table.
   Relies on helpers defined in jobs.js (loaded first). */

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("upload-form");
  const jobsBody = document.getElementById("jobs-table-body");
  const jobDialog = document.getElementById("job-dialog");
  if (!jobsBody || window.__dashboardInitialized) return;
  window.__dashboardInitialized = true;
  let jobsTimer = null;
  let statsTimer = null;

  const stopDashboardPolling = () => {
    if (jobsTimer !== null) window.clearInterval(jobsTimer);
    if (statsTimer !== null) window.clearInterval(statsTimer);
    jobsTimer = null;
    statsTimer = null;
  };
  window.__stopProtectedPolling = stopDashboardPolling;

  if (form) {
    const startBtn = document.getElementById("start-btn");
    const statusEl = document.getElementById("upload-status");
    const pathsInput = document.getElementById("video_paths");
    const sourceInput = document.getElementById("source_lang");
    const targetInput = document.getElementById("target_lang");

    function selectedPaths() {
      return pathsInput.value.split("\n").map((path) => path.trim()).filter(Boolean);
    }

    function hasValidSelection(select) {
      return Boolean(select.value) && [...select.options].some((option) => option.value === select.value);
    }

    function updateStartButton() {
      startBtn.disabled = !selectedPaths().length || !hasValidSelection(sourceInput) || !hasValidSelection(targetInput);
    }

    pathsInput.addEventListener("input", updateStartButton);
    sourceInput.addEventListener("change", updateStartButton);
    targetInput.addEventListener("change", updateStartButton);
    updateStartButton();

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const sourceLang = sourceInput.value;
      const targetLang = targetInput.value;
      const videoPaths = selectedPaths();
      statusEl.className = "status-region";
      statusEl.textContent = "";
      if (!videoPaths.length) {
        statusEl.className = "status-region error";
        statusEl.textContent = "Please select a video file.";
        document.getElementById("browse-btn")?.focus();
        return;
      }
      if (!hasValidSelection(sourceInput)) {
        statusEl.className = "status-region error";
        statusEl.textContent = "Please select a source language.";
        sourceInput.focus();
        return;
      }
      if (!hasValidSelection(targetInput)) {
        statusEl.className = "status-region error";
        statusEl.textContent = "Please select a target language.";
        targetInput.focus();
        return;
      }
      const invalidPath = videoPaths.find((path) => !(/^[A-Za-z]:[\\/]/.test(path) || path.startsWith("/")));
      if (invalidPath) {
        statusEl.className = "status-region error";
        statusEl.textContent = `This path must be absolute: ${invalidPath}`;
        document.getElementById("browse-btn")?.focus();
        return;
      }
      const sourceOption = hasValidSelection(sourceInput);
      const targetOption = hasValidSelection(targetInput);
      if (!sourceOption || !targetOption) {
        statusEl.className = "status-region error";
        statusEl.textContent = "Choose a valid source and target language.";
        (!sourceOption ? document.getElementById("source_lang") : document.getElementById("target_lang")).focus();
        return;
      }

      startBtn.disabled = true;
      statusEl.className = "status-region muted";
      statusEl.textContent = `Queueing ${videoPaths.length} job(s)...`;

      try {
        const res = await fetch("/api/jobs", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ video_paths: videoPaths, source_lang: sourceLang, target_lang: targetLang }),
        });
        handleUnauthorizedResponse(res);
        const body = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(body.detail || `Request failed (${res.status})`);
        statusEl.className = "status-region success";
        statusEl.textContent = "Your jobs are queued. Track progress in Recent Jobs.";
        showNotification("Job queued successfully.", "success");
        form.reset();
        document.getElementById("video_paths")?.dispatchEvent(new Event("input", { bubbles: true }));
        refreshJobsTable();
      } catch (err) {
        statusEl.className = "status-region error";
        statusEl.textContent = "The jobs could not be queued. Check the highlighted fields and try again.";
        showNotification(err.message, "error");
      } finally {
        updateStartButton();
      }
    });
  }

  async function refreshJobsTable() {
    if (!jobsBody) return;
    try {
      const { items } = await fetchJobs({ limit: 8 });
      renderJobsTable(jobsBody, items, { allowDetails: true, allowRetry: window.__CAN_TRIGGER_JOBS__ });
    } catch (err) {
      if (err.code === "AUTH_REQUIRED") return;
      jobsBody.innerHTML = `<tr><td colspan="10" class="error" role="alert">Recent jobs could not be loaded. <button type="button" class="link-btn" data-refresh-jobs>Try again</button></td></tr>`;
      jobsBody.querySelector("[data-refresh-jobs]")?.addEventListener("click", refreshJobsTable, { once: true });
      showNotification(err.message, "error");
    }
  }

  async function refreshStats() {
    const els = {
      total: document.getElementById("stat-total"),
      running: document.getElementById("stat-running"),
      completed: document.getElementById("stat-completed"),
      failed: document.getElementById("stat-failed"),
      cancelled: document.getElementById("stat-cancelled"),
    };
    if (!els.total) return;
    try {
      const stats = await fetchStats();
      els.total.textContent = stats.total;
      els.running.textContent = stats.running;
      els.completed.textContent = stats.completed;
      els.failed.textContent = stats.failed;
      els.cancelled.textContent = stats.cancelled;
    } catch (err) {
      if (err.code === "AUTH_REQUIRED") return;
      /* keep last known values on transient errors */
    }
  }

  if (jobsBody) {
    bindRetryButtons(jobsBody, refreshJobsTable);
    bindCancelButtons(jobsBody, refreshJobsTable);
    if (jobDialog) bindDetailsButtons(jobsBody, jobDialog);
    refreshJobsTable();
    refreshStats();
    jobsTimer = window.setInterval(refreshJobsTable, 3000);
    statsTimer = window.setInterval(refreshStats, 5000);
  }
});
