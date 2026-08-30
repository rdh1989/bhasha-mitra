/* Job history page: filterable, paginated, auto-refreshing table. */

document.addEventListener("DOMContentLoaded", () => {
  const tbody = document.getElementById("jobs-table-body");
  const statusFilter = document.getElementById("filter-status");
  const prevBtn = document.getElementById("prev-page");
  const nextBtn = document.getElementById("next-page");
  const pageIndicator = document.getElementById("page-indicator");
  const dialog = document.getElementById("job-dialog");

  const PAGE_SIZE = 15;
  let offset = 0;
  let total = 0;

  async function load() {
    try {
      const { items, total: newTotal } = await fetchJobs({
        limit: PAGE_SIZE,
        offset,
        status: statusFilter.value,
      });
      total = newTotal;
      renderJobsTable(tbody, items, { allowDelete: window.__IS_ADMIN__, allowDetails: true });
      const page = Math.floor(offset / PAGE_SIZE) + 1;
      const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
      pageIndicator.textContent = `Page ${page} of ${pages} (${total} job${total === 1 ? "" : "s"})`;
      prevBtn.disabled = offset === 0;
      nextBtn.disabled = offset + PAGE_SIZE >= total;
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="7" class="error">${err.message}</td></tr>`;
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
  bindDetailsButtons(tbody, dialog);

  load();
  setInterval(load, 5000);
});
