/* User administration page: create, edit (role/active/password), delete. */

document.addEventListener("DOMContentLoaded", () => {
  const createForm = document.getElementById("create-user-form");
  const createStatus = document.getElementById("create-user-status");
  const tbody = document.getElementById("users-table-body");

  createForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submitButton = createForm.querySelector("button[type=submit]");
    if (submitButton) { submitButton.disabled = true; submitButton.textContent = "Adding user..."; }
    const formData = new FormData(createForm);
    try {
      const res = await fetch("/api/users", { method: "POST", body: formData });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || `Failed to create user (${res.status})`);
      createStatus.className = "status-region success";
      createStatus.textContent = `User '${body.username}' created.`;
      showNotification(`User '${body.username}' created.`, "success");
      createForm.reset();
      setTimeout(() => window.location.reload(), 700);
    } catch (err) {
      createStatus.className = "status-region error";
      createStatus.textContent = "The user could not be created. Review the fields and try again.";
      showNotification(err.message, "error");
    } finally {
      if (submitButton) { submitButton.disabled = false; submitButton.textContent = "Add user"; }
    }
  });

  tbody.addEventListener("click", async (event) => {
    const saveBtn = event.target.closest("[data-save-user]");
    const deleteBtn = event.target.closest("[data-delete-user]");

    if (saveBtn) {
      if (saveBtn.disabled) return;
      const userId = saveBtn.getAttribute("data-save-user");
      const row = tbody.querySelector(`tr[data-user-row="${userId}"]`);
      const rowStatus = row.querySelector(`[data-user-status="${userId}"]`);
      const role = row.querySelector(".role-select").value;
      const isActive = row.querySelector(".active-toggle").checked;
      const passwordInput = row.querySelector(".reset-password");
      const password = passwordInput.value.trim();

      const formData = new FormData();
      formData.append("role", role);
      formData.append("is_active", isActive ? "true" : "false");
      if (password) formData.append("password", password);

      saveBtn.disabled = true;
      saveBtn.classList.add("is-loading");
      saveBtn.textContent = "Saving...";
      if (rowStatus) {
        rowStatus.className = "user-row-status muted";
        rowStatus.textContent = "Saving...";
      }
      try {
        const res = await fetch(`/api/users/${userId}`, { method: "PUT", body: formData });
        const body = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(body.detail || "Failed to update user.");
        passwordInput.value = "";
        if (rowStatus) {
          rowStatus.className = "user-row-status success";
          rowStatus.textContent = "Saved";
        }
        showNotification("User changes saved.", "success");
      } catch (error) {
        if (rowStatus) {
          rowStatus.className = "user-row-status error";
          rowStatus.textContent = "Not saved";
        }
        showNotification(error.message || "Failed to update user.", "error");
      } finally {
        saveBtn.disabled = false;
        saveBtn.classList.remove("is-loading");
        saveBtn.textContent = "Save";
      }
    }

    if (deleteBtn) {
      const userId = deleteBtn.getAttribute("data-delete-user");
      if (!await (window.confirmAppAction?.("Delete this user permanently?", "Delete user") ?? Promise.resolve(false))) return;
      deleteBtn.disabled = true;
      const res = await fetch(`/api/users/${userId}`, { method: "DELETE" });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        deleteBtn.disabled = false;
        showNotification(body.detail || "Failed to delete user.", "error");
        return;
      }
      tbody.querySelector(`tr[data-user-row="${userId}"]`)?.remove();
      showNotification("User deleted.", "success");
    }
  });
});
