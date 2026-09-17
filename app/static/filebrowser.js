/* Server-side file browser dialog for picking local video file paths
   (videos are never uploaded - the server just needs a path it can read). */

document.addEventListener("DOMContentLoaded", () => {
  const browseButtons = [...document.querySelectorAll("[data-browse-kind]")];
  const dialog = document.getElementById("file-browser-dialog");
  if (!browseButtons.length || !dialog) return;

  const currentPathEl = dialog.querySelector(".fb-current-path");
  const entriesEl = document.getElementById("fb-entries");
  const closeBtn = document.getElementById("fb-close");
  const titleEl = document.getElementById("file-browser-title");
  let currentPath = "";
  let activePicker = null;
  let returnFocus = browseButtons[0];

  const pickerFor = (button) => ({
    button,
    kind: button.dataset.browseKind,
    pathsInput: document.getElementById(button.dataset.pathsInput),
    selectedFilesEl: document.getElementById(button.dataset.selectedFiles),
  });
  const filenameForPath = (path) => path.split(/[\\/]/).filter(Boolean).pop() || path;
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));

  function renderSelectedFiles(picker) {
    const paths = picker.pathsInput.value.split("\n").map((path) => path.trim()).filter(Boolean);
    if (!paths.length) {
      picker.selectedFilesEl.innerHTML = `<p class="selected-files-empty">No ${picker.kind} selected</p>`;
      return;
    }
    picker.selectedFilesEl.innerHTML = paths.map((path, index) => {
      const filename = filenameForPath(path);
      return `<div class="selected-file"><svg class="file-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m8 5 10 7-10 7z"></path><path d="M4 5v14"></path></svg><span class="selected-file-name" title="${escapeHtml(filename)}">${escapeHtml(filename)}</span><button type="button" class="remove-file" data-remove-file="${index}" aria-label="Remove ${escapeHtml(filename)}">&times;</button></div>`;
    }).join("");
  }

  const pickers = browseButtons.map(pickerFor);
  pickers.forEach((picker) => {
    picker.pathsInput.addEventListener("input", () => renderSelectedFiles(picker));
    picker.selectedFilesEl.addEventListener("click", (event) => {
      const removeButton = event.target.closest("[data-remove-file]");
      if (!removeButton) return;
      const paths = picker.pathsInput.value.split("\n").map((path) => path.trim()).filter(Boolean);
      paths.splice(Number(removeButton.dataset.removeFile), 1);
      picker.pathsInput.value = paths.join("\n");
      picker.pathsInput.dispatchEvent(new Event("input", { bubbles: true }));
      picker.button.focus();
    });
    renderSelectedFiles(picker);
  });

  function renderEntries(body) {
    const rows = [];
    if (body.parent) rows.push(`<button type="button" class="fb-entry fb-entry-up" data-nav="${escapeHtml(body.parent)}">&#8617; Go up</button>`);
    else if (currentPath) rows.push(`<button type="button" class="fb-entry fb-entry-up" data-nav="">&#8617; Go up</button>`);
    for (const entry of body.entries || []) {
      const action = entry.is_dir ? "data-nav" : "data-select";
      const label = entry.is_dir ? `Open folder ${entry.name}` : `Select ${activePicker.kind} ${entry.name}`;
      rows.push(`<button type="button" class="fb-entry" ${action}="${escapeHtml(entry.path)}" aria-label="${escapeHtml(label)}">${escapeHtml(entry.name)}</button>`);
    }
    entriesEl.innerHTML = rows.length ? rows.join("") : `<p class="fb-empty">No supported ${activePicker.kind} files or folders were found here.</p>`;
  }

  async function loadDirectory(path) {
    entriesEl.innerHTML = `<p class="fb-empty">Loading...</p>`;
    try {
      const params = new URLSearchParams({ kind: activePicker.kind });
      if (path) params.set("path", path);
      const res = await fetch(`/api/browse?${params.toString()}`);
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || `Failed to browse (${res.status})`);
      currentPath = body.path || "";
      currentPathEl.textContent = currentPath || "This PC";
      renderEntries(body);
      entriesEl.querySelector("button")?.focus();
    } catch (_err) {
      entriesEl.innerHTML = `<p class="fb-empty error" role="alert">This folder could not be opened. Try another location.</p>`;
    }
  }

  entriesEl.addEventListener("click", (event) => {
    const navEl = event.target.closest("[data-nav]");
    if (navEl) return loadDirectory(navEl.dataset.nav);
    const selectEl = event.target.closest("[data-select]");
    if (!selectEl) return;
    const filePath = selectEl.dataset.select;
    const paths = activePicker.pathsInput.value.split("\n").map((path) => path.trim()).filter(Boolean);
    if (activePicker.kind === "text") paths.splice(0, paths.length, filePath);
    else if (!paths.includes(filePath)) paths.push(filePath);
    activePicker.pathsInput.value = paths.join("\n");
    activePicker.pathsInput.dispatchEvent(new Event("input", { bubbles: true }));
    dialog.close();
  });

  browseButtons.forEach((button) => button.addEventListener("click", () => {
    activePicker = pickerFor(button);
    returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : button;
    titleEl.textContent = `Choose ${activePicker.kind} files`;
    dialog.showModal();
    loadDirectory(currentPath);
  }));
  closeBtn.addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => window.setTimeout(() => returnFocus?.focus(), 0));
});
