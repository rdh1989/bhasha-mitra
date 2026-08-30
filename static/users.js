/* User administration page: create, edit (role/active/password), delete. */

document.addEventListener("DOMContentLoaded", () => {
  const createForm = document.getElementById("create-user-form");
  const createStatus = document.getElementById("create-user-status");
  const tbody = document.getElementById("users-table-body");

  createForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(createForm);
    try {
      const res = await fetch("/api/users", { method: "POST", body: formData });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || `Failed to create user (${res.status})`);
      createStatus.innerHTML = `<p class="success">User '${body.username}' created.</p>`;
      createForm.reset();
      setTimeout(() => window.location.reload(), 700);
    } catch (err) {
      createStatus.innerHTML = `<p class="error">${err.message}</p>`;
    }
  });

  tbody.addEventListener("click", async (event) => {
    const saveBtn = event.target.closest("[data-save-user]");
    const deleteBtn = event.target.closest("[data-delete-user]");

    if (saveBtn) {
      const userId = saveBtn.getAttribute("data-save-user");
      const row = tbody.querySelector(`tr[data-user-row="${userId}"]`);
      const role = row.querySelector(".role-select").value;
      const isActive = row.querySelector(".active-toggle").checked;
      const passwordInput = row.querySelector(".reset-password");
      const password = passwordInput.value.trim();

      const formData = new FormData();
      formData.append("role", role);
      formData.append("is_active", isActive ? "true" : "false");
      if (password) formData.append("password", password);

      const res = await fetch(`/api/users/${userId}`, { method: "PUT", body: formData });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        alert(body.detail || "Failed to update user.");
        return;
      }
      passwordInput.value = "";
      saveBtn.textContent = "Saved";
      setTimeout(() => (saveBtn.textContent = "Save"), 1200);
    }

    if (deleteBtn) {
      const userId = deleteBtn.getAttribute("data-delete-user");
      if (!confirm("Delete this user permanently?")) return;
      const res = await fetch(`/api/users/${userId}`, { method: "DELETE" });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        alert(body.detail || "Failed to delete user.");
        return;
      }
      tbody.querySelector(`tr[data-user-row="${userId}"]`)?.remove();
    }
  });
});
