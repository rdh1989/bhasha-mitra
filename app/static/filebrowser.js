/* Server-side file browser dialog for picking local video file paths
   (videos are never uploaded - the server just needs a path it can read). */

document.addEventListener("DOMContentLoaded", () => {
  const browseBtn = document.getElementById("browse-btn");
  const dialog = document.getElementById("file-browser-dialog");
  if (!browseBtn || !dialog) return;

  const currentPathEl = dialog.querySelector(".fb-current-path");
  const entriesEl = document.getElementById("fb-entries");
  const closeBtn = document.getElementById("fb-close");
  const pathsInput = document.getElementById("video_paths");
  const selectedFilesEl = document.getElementById("selected-files");

  let currentPath = "";
  let returnFocus = browseBtn;

  function filenameForPath(path) {
    return path.split(/[\\/]/).filter(Boolean).pop() || path;
  }

  function renderSelectedFiles() {
    if (!selectedFilesEl) return;
    const paths = pathsInput.value.split("\n").map((path) => path.trim()).filter(Boolean);
    if (!paths.length) {
      selectedFilesEl.innerHTML = `<p class="selected-files-empty">No video selected</p>`;
      return;
    }
    selectedFilesEl.innerHTML = paths.map((path, index) => {
      const filename = filenameForPath(path);
      return `<div class="selected-file">
        <svg class="file-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m8 5 10 7-10 7z"></path><path d="M4 5v14"></path></svg>
        <span class="selected-file-name" title="${escapeHtml(filename)}">${escapeHtml(filename)}</span>
        <button type="button" class="remove-file" data-remove-file="${index}" aria-label="Remove ${escapeHtml(filename)}">&times;</button>
      </div>`;
    }).join("");
  }

  pathsInput.addEventListener("input", renderSelectedFiles);
  selectedFilesEl?.addEventListener("click", (event) => {
    const removeButton = event.target.closest("[data-remove-file]");
    if (!removeButton) return;
    const paths = pathsInput.value.split("\n").map((path) => path.trim()).filter(Boolean);
    paths.splice(Number(removeButton.getAttribute("data-remove-file")), 1);
    pathsInput.value = paths.join("\n");
    pathsInput.dispatchEvent(new Event("input", { bubbles: true }));
    browseBtn.focus();
  });
  renderSelectedFiles();

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (c) => (
      { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
    ));
  }

  function renderEntries(body) {
    const rows = [];
    if (body.parent) {
      rows.push(`<button type="button" class="fb-entry fb-entry-up" data-nav="${escapeHtml(body.parent)}">&#8617; Go up</button>`);
    } else if (currentPath) {
      // At a drive root (Windows) - ".." goes back to the drive list.
      rows.push(`<button type="button" class="fb-entry fb-entry-up" data-nav="">&#8617; Go up</button>`);
    }
    for (const entry of body.entries || []) {
      const icon = entry.is_dir ? "\u{1F4C1}" : "\u{1F3AC}";
      const action = entry.is_dir ? "data-nav" : "data-select";
      const label = entry.is_dir ? `Open folder ${entry.name}` : `Select video ${entry.name}`;
      rows.push(`<button type="button" class="fb-entry" ${action}="${escapeHtml(entry.path)}" aria-label="${escapeHtml(label)}">${icon} ${escapeHtml(entry.name)}</button>`);
    }
    entriesEl.innerHTML = rows.length ? rows.join("") : `<p class="fb-empty">No supported video files or folders were found here.</p>`;
  }

  async function loadDirectory(path) {
    entriesEl.innerHTML = `<p class="fb-empty">Loading...</p>`;
    try {
      const params = new URLSearchParams();
      if (path) params.set("path", path);
      const res = await fetch(`/api/browse?${params.toString()}`);
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || `Failed to browse (${res.status})`);
      currentPath = body.path || "";
      currentPathEl.textContent = currentPath || "This PC";
      renderEntries(body);
      entriesEl.querySelector("button")?.focus();
    } catch (err) {
      entriesEl.innerHTML = `<p class="fb-empty error" role="alert">This folder could not be opened. Try another location.</p>`;
    }
  }

  entriesEl.addEventListener("click", (event) => {
    const navEl = event.target.closest("[data-nav]");
    if (navEl) {
      loadDirectory(navEl.getAttribute("data-nav"));
      return;
    }
    const selectEl = event.target.closest("[data-select]");
    if (selectEl) {
      const filePath = selectEl.getAttribute("data-select");
      const existing = pathsInput.value.split("\n").map((p) => p.trim()).filter(Boolean);
      if (!existing.includes(filePath)) existing.push(filePath);
      pathsInput.value = existing.join("\n");
      pathsInput.dispatchEvent(new Event("input", { bubbles: true }));
      dialog.close();
    }
  });

  browseBtn.addEventListener("click", () => {
    returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : browseBtn;
    dialog.showModal();
    loadDirectory(currentPath);
  });
  closeBtn.addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => window.setTimeout(() => returnFocus?.focus(), 0));
});
