const API_BASE = window.location.origin + "/api/v1";

const state = {
  accessToken: localStorage.getItem("access_token") || null,
  refreshToken: localStorage.getItem("refresh_token") || null,
  me: null,
  usersPage: 1,
  tasksPage: 1,
};

function showToast(message) {
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2800);
}

async function apiFetch(path, options = {}, retry = true) {
  const headers = options.headers || {};
  if (state.accessToken)
    headers["Authorization"] = `Bearer ${state.accessToken}`;
  if (options.body && !(options.body instanceof URLSearchParams)) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (response.status === 401 && retry && state.refreshToken) {
    const refreshed = await tryRefresh();
    if (refreshed) return apiFetch(path, options, false);
  }

  if (response.status === 204) return null;

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const message = data?.error?.message || "Something went wrong";
    throw new Error(message);
  }
  return data;
}

async function tryRefresh() {
  try {
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: state.refreshToken }),
    });
    if (!response.ok) return false;
    const data = await response.json();
    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

function setTokens(access, refresh) {
  state.accessToken = access;
  state.refreshToken = refresh;
  localStorage.setItem("access_token", access);
  localStorage.setItem("refresh_token", refresh);
}

function clearTokens() {
  state.accessToken = null;
  state.refreshToken = null;
  state.me = null;
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

function showView(name) {
  document
    .querySelectorAll(".view")
    .forEach((el) => el.classList.add("hidden"));
  document.getElementById(`view-${name}`).classList.remove("hidden");
  document.querySelectorAll(".nav button[data-view]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === name);
  });

  if (name === "dashboard") loadDashboard();
  if (name === "users") loadUsers();
  if (name === "departments") loadDepartments();
  if (name === "tasks") loadTasks();
}

function applyRoleVisibility() {
  const role = state.me?.role;
  document
    .getElementById("new-department-btn")
    ?.classList.toggle("hidden", role !== "owner");
  document
    .getElementById("new-user-btn")
    ?.classList.toggle("hidden", role === "employee");
  document
    .getElementById("new-task-btn")
    ?.classList.toggle("hidden", role === "employee");
}

async function loadDashboard() {
  const container = document.getElementById("dashboard-content");
  container.innerHTML = "Loading...";
  try {
    const data = await apiFetch("/stats/overview");
    const roleRows = Object.entries(data.users_by_role)
      .map(
        ([role, count]) =>
          `<div class="stat-row"><span>${role}</span><span>${count}</span></div>`,
      )
      .join("");
    const statusRows = Object.entries(data.tasks_by_status)
      .map(
        ([status, count]) =>
          `<div class="stat-row"><span>${status}</span><span>${count}</span></div>`,
      )
      .join("");
    const deptRows = data.departments
      .map(
        (d) =>
          `<div class="stat-row"><span>${d.name}</span><span>${d.headcount}</span></div>`,
      )
      .join("");
    container.innerHTML = `
      <div class="stat-card"><h3>Users by role</h3>${roleRows || "No data"}</div>
      <div class="stat-card"><h3>Tasks by status</h3>${statusRows || "No data"}</div>
      <div class="stat-card"><h3>Department headcount</h3>${deptRows || "No data"}</div>
    `;
  } catch (err) {
    container.innerHTML = `<p>${err.message}</p>`;
  }
}

async function loadUsers() {
  const search = document.getElementById("user-search").value.trim();
  const query = new URLSearchParams({ page: state.usersPage, size: 10 });
  if (search) query.set("q", search);

  try {
    const data = await apiFetch(`/users?${query}`);
    const tbody = document.getElementById("users-tbody");
    tbody.innerHTML = data.items
      .map(
        (u) => `
        <tr>
          <td>${u.full_name}</td>
          <td>${u.email}</td>
          <td><span class="badge ${u.role}">${u.role}</span></td>
          <td>${u.department_id ?? "-"}</td>
          <td><span class="badge ${u.is_active ? "active" : "inactive"}">${u.is_active ? "active" : "inactive"}</span></td>
          <td>${u.is_active && u.id !== state.me.id ? `<button data-deactivate="${u.id}">Deactivate</button>` : ""}</td>
        </tr>`,
      )
      .join("");

    tbody.querySelectorAll("[data-deactivate]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          await apiFetch(`/users/${btn.dataset.deactivate}/deactivate`, {
            method: "POST",
          });
          showToast("User deactivated");
          loadUsers();
        } catch (err) {
          showToast(err.message);
        }
      });
    });

    renderPager("users-pager", data, (page) => {
      state.usersPage = page;
      loadUsers();
    });
  } catch (err) {
    showToast(err.message);
  }
}

async function loadDepartments() {
  try {
    const data = await apiFetch(`/departments/headcount`);
    const tbody = document.getElementById("departments-tbody");
    tbody.innerHTML = data
      .map(
        (d) => `
        <tr>
          <td>${d.name}</td>
          <td>${d.headcount}</td>
          <td>${state.me.role === "owner" ? `<button data-delete-dept="${d.id}">Delete</button>` : ""}</td>
        </tr>`,
      )
      .join("");

    tbody.querySelectorAll("[data-delete-dept]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          await apiFetch(`/departments/${btn.dataset.deleteDept}`, {
            method: "DELETE",
          });
          showToast("Department deleted");
          loadDepartments();
        } catch (err) {
          showToast(err.message);
        }
      });
    });
  } catch (err) {
    showToast(err.message);
  }
}

async function loadTasks() {
  const query = new URLSearchParams({ page: state.tasksPage, size: 10 });
  try {
    const data = await apiFetch(`/tasks/with-names?${query}`);
    const tbody = document.getElementById("tasks-tbody");
    tbody.innerHTML = data.items
      .map(
        (t) => `
        <tr>
          <td>${t.title}</td>
          <td>
            <select data-status="${t.id}">
              ${["todo", "in_progress", "done"].map((s) => `<option value="${s}" ${s === t.status ? "selected" : ""}>${s}</option>`).join("")}
            </select>
          </td>
          <td>${t.priority}</td>
          <td>${t.assignee_name ?? "-"}</td>
          <td>${t.due_date ?? "-"}</td>
          <td></td>
        </tr>`,
      )
      .join("");

    tbody.querySelectorAll("[data-status]").forEach((select) => {
      select.addEventListener("change", async () => {
        try {
          await apiFetch(`/tasks/${select.dataset.status}/status`, {
            method: "PATCH",
            body: JSON.stringify({ status: select.value }),
          });
          showToast("Task updated");
        } catch (err) {
          showToast(err.message);
          loadTasks();
        }
      });
    });

    renderPager("tasks-pager", data, (page) => {
      state.tasksPage = page;
      loadTasks();
    });
  } catch (err) {
    showToast(err.message);
  }
}

function renderPager(elementId, page, onChange) {
  const el = document.getElementById(elementId);
  el.innerHTML = "";

  const prev = document.createElement("button");
  prev.textContent = "Previous";
  prev.disabled = page.page <= 1;
  prev.addEventListener("click", () => onChange(page.page - 1));

  const label = document.createElement("span");
  label.textContent = `Page ${page.page} of ${page.pages || 1}`;

  const next = document.createElement("button");
  next.textContent = "Next";
  next.disabled = page.page >= page.pages;
  next.addEventListener("click", () => onChange(page.page + 1));

  el.append(prev, label, next);
}

function openModal(title, fields, onSubmit) {
  const root = document.getElementById("modal-root");
  const fieldsHtml = fields
    .map((f) => {
      if (f.type === "select") {
        return `<label>${f.label}<select name="${f.name}">${f.options.map((o) => `<option value="${o}">${o}</option>`).join("")}</select></label>`;
      }
      return `<label>${f.label}<input type="${f.type || "text"}" name="${f.name}" ${f.required ? "required" : ""}></label>`;
    })
    .join("");

  root.innerHTML = `
    <div class="modal-backdrop">
      <div class="modal">
        <h2>${title}</h2>
        <form class="form" id="modal-form">
          ${fieldsHtml}
          <p class="error" id="modal-error"></p>
          <div class="modal-actions">
            <button type="button" class="cancel">Cancel</button>
            <button type="submit" class="submit">Save</button>
          </div>
        </form>
      </div>
    </div>
  `;

  root
    .querySelector(".cancel")
    .addEventListener("click", () => (root.innerHTML = ""));
  root.querySelector("#modal-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const payload = Object.fromEntries(formData.entries());
    try {
      await onSubmit(payload);
      root.innerHTML = "";
    } catch (err) {
      document.getElementById("modal-error").textContent = err.message;
    }
  });
}

function wireModals() {
  document
    .getElementById("new-department-btn")
    ?.addEventListener("click", () => {
      openModal(
        "New department",
        [{ label: "Name", name: "name", required: true }],
        async (payload) => {
          await apiFetch("/departments", {
            method: "POST",
            body: JSON.stringify(payload),
          });
          showToast("Department created");
          loadDepartments();
        },
      );
    });

  document.getElementById("new-user-btn")?.addEventListener("click", () => {
    const roleOptions =
      state.me.role === "owner"
        ? ["employee", "manager", "owner"]
        : ["employee"];
    openModal(
      "New user",
      [
        { label: "Full name", name: "full_name", required: true },
        { label: "Email", name: "email", type: "email", required: true },
        {
          label: "Password",
          name: "password",
          type: "password",
          required: true,
        },
        { label: "Role", name: "role", type: "select", options: roleOptions },
      ],
      async (payload) => {
        await apiFetch("/users", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        showToast("User created");
        loadUsers();
      },
    );
  });

  document.getElementById("new-task-btn")?.addEventListener("click", () => {
    openModal(
      "New task",
      [
        { label: "Title", name: "title", required: true },
        { label: "Description", name: "description" },
        { label: "Assignee user id", name: "assignee_id" },
        {
          label: "Priority",
          name: "priority",
          type: "select",
          options: ["low", "medium", "high"],
        },
      ],
      async (payload) => {
        if (payload.assignee_id)
          payload.assignee_id = Number(payload.assignee_id);
        else delete payload.assignee_id;
        await apiFetch("/tasks", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        showToast("Task created");
        loadTasks();
      },
    );
  });
}

async function enterApp() {
  try {
    state.me = await apiFetch("/auth/me");
  } catch {
    clearTokens();
    showAuthView();
    return;
  }
  document.getElementById("nav").classList.remove("hidden");
  document.getElementById("view-auth").classList.add("hidden");
  applyRoleVisibility();
  showView("dashboard");
}

function showAuthView() {
  document.getElementById("nav").classList.add("hidden");
  document
    .querySelectorAll(".view")
    .forEach((el) => el.classList.add("hidden"));
  document.getElementById("view-auth").classList.remove("hidden");
}

function wireAuth() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document
        .querySelectorAll(".tab")
        .forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      document
        .getElementById("login-form")
        .classList.toggle("hidden", tab.dataset.tab !== "login");
      document
        .getElementById("register-form")
        .classList.toggle("hidden", tab.dataset.tab !== "register");
    });
  });

  document
    .getElementById("login-form")
    .addEventListener("submit", async (e) => {
      e.preventDefault();
      const errorEl = document.getElementById("login-error");
      errorEl.textContent = "";
      const formData = new FormData(e.target);
      try {
        const response = await fetch(`${API_BASE}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({
            username: formData.get("email"),
            password: formData.get("password"),
          }),
        });
        const data = await response.json();
        if (!response.ok)
          throw new Error(data?.error?.message || "Login failed");
        setTokens(data.access_token, data.refresh_token);
        enterApp();
      } catch (err) {
        errorEl.textContent = err.message;
      }
    });

  document
    .getElementById("register-form")
    .addEventListener("submit", async (e) => {
      e.preventDefault();
      const errorEl = document.getElementById("register-error");
      errorEl.textContent = "";
      const formData = new FormData(e.target);
      const payload = Object.fromEntries(formData.entries());
      try {
        const response = await fetch(`${API_BASE}/organizations/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok)
          throw new Error(data?.error?.message || "Registration failed");
        showToast("Organization created, please log in");
        document.querySelector('.tab[data-tab="login"]').click();
      } catch (err) {
        errorEl.textContent = err.message;
      }
    });
}

function wireNav() {
  document.querySelectorAll(".nav button[data-view]").forEach((btn) => {
    btn.addEventListener("click", () => showView(btn.dataset.view));
  });

  document.getElementById("logout-btn").addEventListener("click", async () => {
    try {
      if (state.refreshToken) {
        await apiFetch("/auth/logout", {
          method: "POST",
          body: JSON.stringify({ refresh_token: state.refreshToken }),
        });
      }
    } catch {
      clearTokens();
    }
    clearTokens();
    showAuthView();
  });

  document.getElementById("user-search").addEventListener(
    "input",
    debounce(() => {
      state.usersPage = 1;
      loadUsers();
    }, 350),
  );
}

function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

wireAuth();
wireNav();
wireModals();

if (state.accessToken) {
  enterApp();
} else {
  showAuthView();
}
