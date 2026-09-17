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
  let textJobId = null;

  const tabs = [...document.querySelectorAll("[data-translation-tab]")];
  const panels = [...document.querySelectorAll("[data-translation-panel]")];
  tabs.forEach((tab) => tab.addEventListener("click", () => {
    const mode = tab.dataset.translationTab;
    tabs.forEach((item) => item.setAttribute("aria-selected", String(item === tab)));
    panels.forEach((panel) => { panel.hidden = panel.dataset.translationPanel !== mode; });
  }));

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

  const audioForm = document.getElementById("audio-form");
  if (audioForm) {
    const audioPaths = document.getElementById("audio_paths");
    const source = document.getElementById("audio_source_lang");
    const target = document.getElementById("audio_target_lang");
    const start = document.getElementById("audio-start-btn");
    const status = document.getElementById("audio-status");
    const selected = () => audioPaths.value.split("\n").map((path) => path.trim()).filter(Boolean);
    const valid = (select) => Boolean(select.value) && [...select.options].some((option) => option.value === select.value);
    const update = () => { start.disabled = !selected().length || !valid(source) || !valid(target); };
    audioPaths.addEventListener("input", update);
    source.addEventListener("change", update);
    target.addEventListener("change", update);
    update();
    audioForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const paths = selected();
      if (!paths.length || !valid(source) || !valid(target)) return update();
      start.disabled = true;
      status.className = "status-region muted";
      status.textContent = `Queueing ${paths.length} audio job(s)...`;
      try {
        const res = await fetch("/api/audio/jobs", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ audio_paths: paths, source_lang: source.value, target_lang: target.value }),
        });
        handleUnauthorizedResponse(res);
        const body = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(body.detail || `Request failed (${res.status})`);
        status.className = "status-region success";
        status.textContent = "Your audio jobs are queued. Track progress in Recent Jobs.";
        audioForm.reset();
        audioPaths.dispatchEvent(new Event("input", { bubbles: true }));
        refreshJobsTable();
      } catch (err) {
        status.className = "status-region error";
        status.textContent = "The audio jobs could not be queued. Try again.";
        showNotification(err.message, "error");
      } finally {
        update();
      }
    });
  }

  const textForm = document.getElementById("text-form");
  if (textForm) {
    const input = document.getElementById("text-input");
    const textPaths = document.getElementById("text_paths");
    const source = document.getElementById("text_source_lang");
    const target = document.getElementById("text_target_lang");
    const start = document.getElementById("text-start-btn");
    const status = document.getElementById("text-status");
    const result = document.getElementById("text-result");
    const translated = document.getElementById("translated-text");
    const download = document.getElementById("download-translation-btn");
    const inputTabs = [...document.querySelectorAll("[data-text-input-tab]")];
    const inputPanels = [...document.querySelectorAll("[data-text-input-panel]")];
    let inputMode = "direct";
    inputTabs.forEach((tab) => tab.addEventListener("click", () => {
      inputMode = tab.dataset.textInputTab;
      inputTabs.forEach((item) => item.setAttribute("aria-selected", String(item === tab)));
      inputPanels.forEach((panel) => { panel.hidden = panel.dataset.textInputPanel !== inputMode; });
    }));
    textForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const text = input.value.trim();
      const textPath = textPaths.value.trim();
      if (!source.value || !target.value || (inputMode === "direct" ? !text : !textPath)) return;
      start.disabled = true;
      result.hidden = true;
      status.className = "status-region muted";
      status.textContent = "Queueing text translation...";
      try {
        const res = await fetch("/api/text/jobs", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: inputMode === "direct" ? text : "",
            text_path: inputMode === "file" ? textPath : null,
            source_lang: source.value,
            target_lang: target.value,
          }),
        });
        handleUnauthorizedResponse(res);
        const body = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(body.detail || `Request failed (${res.status})`);
        textJobId = body.job_id;
        download.hidden = true;
        status.className = "status-region muted";
        status.textContent = "Text translation queued.";
        refreshJobsTable();
      } catch (err) {
        status.className = "status-region error";
        status.textContent = "The text could not be translated. Try again.";
        showNotification(err.message, "error");
      } finally {
        start.disabled = false;
      }
    });
    document.getElementById("copy-translation-btn")?.addEventListener("click", async () => {
      await navigator.clipboard?.writeText(translated.textContent || "");
    });
  }

  async function refreshJobsTable() {
    if (!jobsBody) return;
    try {
      const { items } = await fetchJobs({ limit: 8 });
      renderJobsTable(jobsBody, items, { allowDetails: true, allowRetry: window.__CAN_TRIGGER_JOBS__ });
      await refreshTextJob();
    } catch (err) {
      if (err.code === "AUTH_REQUIRED") return;
      jobsBody.innerHTML = `<tr><td colspan="10" class="error" role="alert">Recent jobs could not be loaded. <button type="button" class="link-btn" data-refresh-jobs>Try again</button></td></tr>`;
      jobsBody.querySelector("[data-refresh-jobs]")?.addEventListener("click", refreshJobsTable, { once: true });
      showNotification(err.message, "error");
    }
  }

  async function refreshTextJob() {
    if (!textJobId) return;
    const status = document.getElementById("text-status");
    const result = document.getElementById("text-result");
    const translated = document.getElementById("translated-text");
    const download = document.getElementById("download-translation-btn");
    try {
      const res = await fetch(`/api/jobs/${encodeURIComponent(textJobId)}`);
      handleUnauthorizedResponse(res);
      if (!res.ok) throw new Error("Text job status could not be loaded.");
      const job = await res.json();
      if (!job.done) {
        status.className = "status-region muted";
        status.textContent = job.message || "Translating text...";
        return;
      }
      if (job.stage !== "completed" || !job.has_output) {
        status.className = "status-region error";
        status.textContent = job.error || job.message || "Text translation failed.";
        textJobId = null;
        return;
      }
      const outputUrl = `/media/output/${encodeURIComponent(textJobId)}`;
      const output = await fetch(outputUrl);
      if (!output.ok) throw new Error("Translated text could not be loaded.");
      translated.textContent = await output.text();
      result.hidden = false;
      download.href = outputUrl;
      download.hidden = false;
      status.className = "status-region success";
      status.textContent = "Translation ready.";
      textJobId = null;
    } catch (err) {
      if (err.code === "AUTH_REQUIRED") return;
      status.className = "status-region error";
      status.textContent = err.message || "Text job status could not be loaded.";
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
