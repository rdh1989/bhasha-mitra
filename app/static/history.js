/* Job history page: filterable, paginated, auto-refreshing table. */

document.addEventListener("DOMContentLoaded", () => {
  const tbody = document.getElementById("jobs-table-body");
  const statusFilter = document.getElementById("filter-status");
  const prevBtn = document.getElementById("prev-page");
  const nextBtn = document.getElementById("next-page");
  const pageIndicator = document.getElementById("page-indicator");
  const dialog = document.getElementById("job-dialog");
  if (!tbody || window.__historyInitialized) return;
  window.__historyInitialized = true;

  const PAGE_SIZE = 15;
  let offset = 0;
  let total = 0;
  let historyTimer = null;

  const stopHistoryPolling = () => {
    if (historyTimer !== null) window.clearInterval(historyTimer);
    historyTimer = null;
  };
  window.__stopProtectedPolling = stopHistoryPolling;

  async function load() {
    tbody.innerHTML = `<tr><td colspan="10" class="loading-cell">Loading job history...</td></tr>`;
    try {
      const { items, total: newTotal } = await fetchJobs({
        limit: PAGE_SIZE,
        offset,
        status: statusFilter.value,
      });
      total = newTotal;
      renderJobsTable(tbody, items, {
        allowDelete: window.__IS_ADMIN__,
        allowDetails: true,
        allowRetry: window.__CAN_TRIGGER_JOBS__,
      });
      const page = Math.floor(offset / PAGE_SIZE) + 1;
      const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
      pageIndicator.textContent = `Page ${page} of ${pages} (${total} job${total === 1 ? "" : "s"})`;
      prevBtn.disabled = offset === 0;
      nextBtn.disabled = offset + PAGE_SIZE >= total;
    } catch (err) {
      if (err.code === "AUTH_REQUIRED") return;
      tbody.innerHTML = `<tr><td colspan="10" class="error" role="alert">Job history could not be loaded. <button type="button" class="link-btn" data-refresh-history>Try again</button></td></tr>`;
      tbody.querySelector("[data-refresh-history]")?.addEventListener("click", load, { once: true });
      showNotification(err.message, "error");
    }
  }

  statusFilter.addEventListener("change", () => {
    offset = 0;
    load();
  });
  prevBtn.addEventListener("click", () => {
    offset = Math.max(0, offset - PAGE_SIZE);
    load();
  });
  nextBtn.addEventListener("click", () => {
    offset += PAGE_SIZE;
    load();
  });

  bindDeleteButtons(tbody, load);
  bindRetryButtons(tbody, load);
  bindCancelButtons(tbody, load);
  bindDetailsButtons(tbody, dialog);

  load();
  historyTimer = window.setInterval(load, 5000);
});
