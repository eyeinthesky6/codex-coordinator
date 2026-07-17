"use strict";

const state = {
  snapshot: null,
  filter: "live",
  projectId: "overall",
  nextScanAt: null,
  timer: null,
  doctorTimer: null,
  taskRenderKey: "",
};

const statusLabels = {
  active: "Working now",
  queued: "Queued",
  assigned: "Assigned",
  blocked: "Blocked",
  paused: "Paused",
  idle: "Idle",
  ready: "Done",
};

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

function relativeTime(value) {
  if (!value) return "No recent receipt";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Recently";
  const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
  if (seconds < 15) return "Just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function cadenceLabel(seconds) {
  if (seconds === 60) return "Every 1 minute";
  if (seconds < 3600) return `Every ${Math.floor(seconds / 60)} minutes`;
  return `Every ${Math.floor(seconds / 3600)} hours`;
}

function compactNumber(value) {
  const number = Number(value || 0);
  if (number < 1000) return String(number);
  return `${(number / 1000).toFixed(number >= 10000 ? 0 : 1)}k`;
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "Mission Control request failed");
  return body;
}

function setMetric(id, value) {
  document.getElementById(id).textContent = String(value ?? 0);
}

function renderMetrics(snapshot) {
  setMetric("metric-active", snapshot.metrics.active);
  setMetric("metric-attention", snapshot.metrics.attention);
  setMetric("metric-completed", snapshot.metrics.completedToday);
  const parts = [];
  if (snapshot.metrics.overlaps) parts.push(`${snapshot.metrics.overlaps} ${snapshot.metrics.overlaps === 1 ? "conflict" : "conflicts"}`);
  if (snapshot.metrics.blockers) parts.push(`${snapshot.metrics.blockers} ${snapshot.metrics.blockers === 1 ? "blocker" : "blockers"}`);
  document.getElementById("metric-action-label").textContent = parts.join(" · ") || "no conflicts or blockers";
}

function conflictTaskKeys(snapshot) {
  return new Set(snapshot.conflicts.flatMap((conflict) => conflict.tasks || []));
}

function actionTaskKeys(snapshot) {
  const keys = conflictTaskKeys(snapshot);
  snapshot.tasks.forEach((task) => {
    if (task.attention || ["blocked", "paused"].includes(task.status)) keys.add(task.key);
  });
  return keys;
}

function landedToday(task, snapshot) {
  if (task.status !== "ready" || !task.receiptComplete || !task.updatedAt) return false;
  try {
    const updated = new Date(task.updatedAt);
    const generated = new Date(snapshot.generatedAt);
    return updated.getFullYear() === generated.getFullYear()
      && updated.getMonth() === generated.getMonth()
      && updated.getDate() === generated.getDate();
  } catch (error) {
    return false;
  }
}

function filteredSnapshot(snapshot) {
  const tasks = state.projectId === "overall"
    ? snapshot.tasks
    : snapshot.tasks.filter((task) => task.projectId === state.projectId);
  const taskKeys = new Set(tasks.map((task) => task.key));
  const conflicts = snapshot.conflicts.filter((conflict) => (conflict.tasks || []).every((key) => taskKeys.has(key)));
  const view = { ...snapshot, tasks, conflicts };
  const actions = actionTaskKeys(view);
  view.metrics = {
    active: tasks.filter((task) => ["active", "queued", "assigned"].includes(task.status)).length,
    attention: actions.size,
    overlaps: conflicts.length,
    blockers: tasks.filter((task) => task.attention || ["blocked", "paused"].includes(task.status)).length,
    completedToday: tasks.filter((task) => landedToday(task, snapshot)).length,
  };
  return view;
}

function renderProjects(snapshot) {
  const tabs = document.getElementById("project-tabs");
  const projects = new Map();
  (snapshot.projects || []).forEach((project) => {
    if (project.enabled && project.id && project.name) projects.set(project.id, project.name);
  });
  snapshot.tasks.forEach((task) => {
    if (task.projectId && task.project) projects.set(task.projectId, task.project);
  });
  if (state.projectId !== "overall" && !projects.has(state.projectId)) state.projectId = "overall";
  tabs.replaceChildren();
  const options = [["overall", "Overall"], ...Array.from(projects.entries()).sort((left, right) => left[1].localeCompare(right[1]))];
  options.forEach(([id, label]) => {
    const button = element("button", "project-tab", label);
    button.type = "button";
    button.dataset.project = id;
    const active = id === state.projectId;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
    button.addEventListener("click", () => setProject(id));
    tabs.append(button);
  });
}

function taskVisible(task, snapshot) {
  if (state.filter === "all") return true;
  if (state.filter === "done") return landedToday(task, snapshot);
  if (state.filter === "action") return actionTaskKeys(snapshot).has(task.key);
  return ["active", "queued", "assigned"].includes(task.status);
}

function taskTitle(task) {
  const title = String(task.title || "Untitled Codex task").trim();
  const owner = String(task.owner || "").trim();
  const titleIsGoal = task.coordinationGoal && title.toLowerCase() === String(task.coordinationGoal).toLowerCase();
  const ownerLooksLikeThread = owner && !/^(codex agent|task agent|agent)$/i.test(owner);
  if (titleIsGoal && !task.openUrl && !ownerLooksLikeThread) return "Project coordination";
  return titleIsGoal && ownerLooksLikeThread ? owner : title;
}

function taskActor(task) {
  const owner = String(task.owner || "").trim();
  return owner && owner.toLowerCase() !== taskTitle(task).toLowerCase()
    ? owner
    : (task.role || "Codex agent");
}

function userNextStep(task, snapshot) {
  const conflict = snapshot.conflicts.find((item) => (item.tasks || []).includes(task.key));
  if (conflict?.action) return conflict.action;
  if (task.status === "blocked") {
    return task.openUrl ? "Open the task and decide how to clear the blocker." : "Review the project blocker and decide the next step.";
  }
  if (task.status === "paused") {
    return task.openUrl ? "Open the task, review its resume condition, and decide whether to continue." : "Review the paused work and decide whether to resume it.";
  }
  if (task.status === "ready") return "Review the result, then close or continue the task.";
  if (task.status === "idle") return "Open the task if you want work to continue.";
  if (task.status === "queued") return "No action now — waiting for Codex to start.";
  if (task.status === "assigned") return "No action now — waiting for the next progress update.";
  return "No action now — work is still in progress.";
}

function taskCard(task, snapshot) {
  const card = element("article", "task-card");
  card.dataset.status = task.status;

  const main = element("div", "task-main");
  const meta = element("div", "task-meta");
  meta.append(element("span", "status-pill", statusLabels[task.status] || "Tracked"));
  meta.append(element("span", "project-pill", task.project));
  main.append(meta);
  const displayTitle = taskTitle(task);
  const heading = element("h3", "task-title", displayTitle);
  heading.title = displayTitle;
  main.append(heading);
  const action = userNextStep(task, snapshot);
  const next = element("p", "task-next");
  next.title = task.attention || action;
  next.append(element("strong", "", "Next:"), document.createTextNode(` ${action}`));
  main.append(next);

  const foot = element("div", "task-foot");
  foot.append(element("span", "task-owner", taskActor(task)));
  foot.append(element("span", "task-time", relativeTime(task.updatedAt)));
  main.append(foot);
  card.append(main);

  if (task.openUrl) {
    const link = element("a", "task-action", "Open in Codex");
    link.href = task.openUrl;
    link.setAttribute("aria-label", `Open ${displayTitle} in Codex`);
    link.append(element("span", "", "↗"));
    card.append(link);
  }
  return card;
}

function renderTasks(snapshot) {
  const list = document.getElementById("task-list");
  const visible = snapshot.tasks.filter((task) => taskVisible(task, snapshot));
  const labels = {
    live: `${visible.length} ${visible.length === 1 ? "task" : "tasks"} in motion`,
    action: `${visible.length} ${visible.length === 1 ? "task needs" : "tasks need"} action`,
    done: `${visible.length} ${visible.length === 1 ? "task landed" : "tasks landed"} today`,
    all: `${visible.length} recent ${visible.length === 1 ? "task" : "tasks"}`,
  };
  document.getElementById("workboard-title").textContent = labels[state.filter] || labels.live;
  const renderKey = JSON.stringify({
    filter: state.filter,
    tasks: visible.map((task) => [task.key, taskTitle(task), task.status, taskActor(task), userNextStep(task, snapshot)]),
  });
  if (renderKey === state.taskRenderKey) return;
  state.taskRenderKey = renderKey;
  list.replaceChildren();
  if (!visible.length) {
    const empty = element("div", "empty-tasks");
    const copy = element("div");
    copy.append(element("strong", "", state.filter === "live" ? "The runway is clear" : "Nothing in this view"));
    copy.append(element("p", "", state.filter === "live" ? "Start a Codex task and it will appear here on the next local scan." : "Try another summary card or filter."));
    empty.append(copy);
    list.append(empty);
    return;
  }
  visible.forEach((task) => list.append(taskCard(task, snapshot)));
}

function renderActions(snapshot) {
  const list = document.getElementById("conflict-list");
  list.replaceChildren();
  const conflictKeys = conflictTaskKeys(snapshot);
  const blockers = snapshot.tasks.filter(
    (task) => (task.attention || ["blocked", "paused"].includes(task.status)) && !conflictKeys.has(task.key),
  );
  document.getElementById("signal-count").textContent = String(snapshot.metrics.attention);
  const summary = document.getElementById("overlap-summary");
  if (!snapshot.conflicts.length && !blockers.length) {
    summary.textContent = "No confirmed path conflict or blocked work in this view.";
    const clear = element("div", "clear-state");
    const copy = element("div");
    copy.append(element("strong", "", "No action needed"));
    copy.append(element("p", "", "The collector found no issue that needs a reviewer."));
    clear.append(copy);
    list.append(clear);
    return;
  }
  const parts = [];
  if (snapshot.conflicts.length) parts.push(`${snapshot.conflicts.length} confirmed path ${snapshot.conflicts.length === 1 ? "conflict" : "conflicts"}`);
  if (blockers.length) parts.push(`${blockers.length} blocked or paused ${blockers.length === 1 ? "task" : "tasks"}`);
  summary.textContent = `${parts.join(" · ")}. Open Action to review the affected tasks.`;
  snapshot.conflicts.slice(0, 3).forEach((conflict) => {
    const card = element("article", "conflict-card");
    card.dataset.severity = conflict.severity;
    const top = element("div", "conflict-top");
    top.append(element("strong", "", conflict.title));
    top.append(element("span", "", conflict.project));
    card.append(top, element("p", "", conflict.detail));
    if (conflict.action) card.append(element("p", "conflict-action", conflict.action));
    list.append(card);
  });
  blockers.slice(0, Math.max(0, 4 - snapshot.conflicts.length)).forEach((task) => {
    const card = element("article", "conflict-card");
    card.dataset.severity = task.status === "blocked" ? "high" : "watch";
    const top = element("div", "conflict-top");
    top.append(element("strong", "", taskTitle(task)));
    top.append(element("span", "", `${statusLabels[task.status] || "Needs action"} · ${task.project}`));
    const next = userNextStep(task, snapshot);
    const action = element("p", "conflict-action", `Next: ${next}`);
    action.title = task.attention || next;
    card.append(top, action);
    list.append(card);
  });
}

function setDoctorBullets(items) {
  const summary = document.getElementById("doctor-summary");
  const safeItems = items.filter(Boolean).slice(0, 3);
  summary.replaceChildren(...safeItems.map((item) => element("li", "", item)));
}

function briefDoctorSummary(value) {
  const sentences = String(value || "")
    .split(/(?<=[.!?])\s+/)
    .map((item) => item.trim())
    .filter(Boolean);
  const selected = [];
  [/(installed|source current|checks? passed)/i, /(projects? checked|checked enabled projects?)/i, /(findings?|needs? (coordinator )?review)/i].forEach((pattern) => {
    const match = sentences.find((item) => !selected.includes(item) && pattern.test(item));
    if (match) selected.push(match);
  });
  selected.push(...sentences.filter((item) => !selected.includes(item) && !/doctor run finished/i.test(item)));
  return selected.slice(0, 3).map((item) => {
    const plain = item.replace(/[`*_]+/g, "");
    return plain.length > 180 ? `${plain.slice(0, 179).trim()}…` : plain;
  });
}

function setDoctorHealth(state) {
  const icon = document.getElementById("doctor-health-icon");
  icon.className = `doctor-health-icon is-${state}`;
}

function renderDoctor(doctor = {}) {
  const button = document.getElementById("doctor-run-button");
  const label = document.getElementById("doctor-button-label");
  const status = document.getElementById("doctor-status");
  const lastRun = document.getElementById("doctor-last-run");
  const result = doctor.lastResult || "never";
  button.disabled = Boolean(doctor.running);
  button.classList.toggle("is-running", Boolean(doctor.running));
  button.title = "Project review uses GPT-5.6 Sol · Medium reasoning";
  label.textContent = doctor.running ? "Doctor running" : "Run Doctor";
  if (doctor.running) {
    setDoctorHealth("running");
    setDoctorBullets(["Checking the installed Coordinator and enabled projects."]);
    status.textContent = "Running safely in the background";
  } else if (result === "success") {
    const healthy = doctor.health === "healthy";
    setDoctorHealth(healthy ? "healthy" : "review");
    setDoctorBullets(Array.isArray(doctor.bullets) && doctor.bullets.length
      ? doctor.bullets
      : briefDoctorSummary(doctor.summary || "Doctor completed without a readable summary."));
    status.textContent = healthy ? "All checks clear" : "Review needed";
  } else if (result === "failed") {
    setDoctorHealth("failed");
    setDoctorBullets([doctor.error || "Doctor could not complete its last run."]);
    status.textContent = "Last run needs attention";
  } else {
    setDoctorHealth("idle");
    setDoctorBullets(["Validate the installed Coordinator and enabled projects."]);
    status.textContent = "Ready";
  }
  const configuredModel = "gpt-5.6-sol";
  const doctorModels = {"gpt-5.6-sol": "GPT-5.6 Sol", "gpt-5.5": "GPT-5.5"};
  const modelLabel = doctorModels[doctor.model] || doctor.model || "";
  const historicalModel = Boolean(doctor.lastRunAt && doctor.model && doctor.model !== configuredModel);
  lastRun.textContent = doctor.lastRunAt
    ? `${historicalModel ? "Previous result" : "Last run"} · ${relativeTime(doctor.lastRunAt)}${modelLabel ? ` · ${modelLabel} · ${doctor.reasoning || "medium"}` : ""}`
    : "Next project review · GPT-5.6 Sol · medium";
}

function renderFreshness(snapshot) {
  const seconds = snapshot.settings.refresh_seconds;
  state.nextScanAt = Date.now() + seconds * 1000;
  document.getElementById("collector-cadence").textContent = cadenceLabel(seconds);
  document.getElementById("last-updated").textContent = `Local state updated ${relativeTime(snapshot.generatedAt)}`;
  document.getElementById("live-label").textContent = "Live · local only";
  updateCountdown();
}

function render(snapshot) {
  state.snapshot = snapshot;
  renderProjects(snapshot);
  const view = filteredSnapshot(snapshot);
  renderMetrics(view);
  renderTasks(view);
  renderActions(view);
  renderDoctor(snapshot.doctor);
  renderFreshness(snapshot);
  if (snapshot.doctor?.running) scheduleDoctorPolling();
}

function setFilter(filter, shouldScroll = false) {
  state.filter = filter;
  state.taskRenderKey = "";
  document.querySelectorAll("[data-filter]").forEach((item) => {
    const active = item.dataset.filter === filter;
    item.classList.toggle("is-active", active && item.classList.contains("filter-tab"));
    item.classList.toggle("metric-primary", active && item.classList.contains("metric"));
    item.setAttribute("aria-pressed", String(active));
  });
  if (state.snapshot) renderTasks(filteredSnapshot(state.snapshot));
  if (shouldScroll) document.getElementById("workboard").scrollIntoView({ behavior: "smooth", block: "start" });
}

function setProject(projectId) {
  state.projectId = projectId;
  state.taskRenderKey = "";
  if (state.snapshot) render(state.snapshot);
}

function updateCountdown() {
  const label = document.getElementById("collector-next");
  if (!state.nextScanAt) {
    label.textContent = "Local scan starting…";
    return;
  }
  const remaining = Math.max(0, Math.ceil((state.nextScanAt - Date.now()) / 1000));
  if (remaining <= 1) label.textContent = "Scanning local state…";
  else if (remaining < 60) label.textContent = `Next scan in ${remaining}s`;
  else label.textContent = `Next scan in ${Math.ceil(remaining / 60)}m`;
}

function schedulePolling() {
  window.clearInterval(state.timer);
  state.timer = window.setInterval(async () => {
    updateCountdown();
    if (state.nextScanAt && Date.now() >= state.nextScanAt) {
      try {
        render(await request("/api/refresh", { method: "POST", body: "{}" }));
      } catch (error) {
        document.getElementById("live-label").textContent = "Local collector unavailable";
      }
    }
  }, 1000);
}

async function refreshNow() {
  const button = document.getElementById("refresh-button");
  button.classList.add("is-spinning");
  button.disabled = true;
  try {
    render(await request("/api/refresh", { method: "POST", body: "{}" }));
  } finally {
    window.setTimeout(() => button.classList.remove("is-spinning"), 250);
    button.disabled = false;
  }
}

function scheduleDoctorPolling() {
  if (state.doctorTimer) return;
  state.doctorTimer = window.setInterval(async () => {
    try {
      const snapshot = await request("/api/snapshot");
      render(snapshot);
      if (!snapshot.doctor?.running) {
        window.clearInterval(state.doctorTimer);
        state.doctorTimer = null;
      }
    } catch (error) {
      window.clearInterval(state.doctorTimer);
      state.doctorTimer = null;
      setDoctorHealth("failed");
      setDoctorBullets([error.message]);
      document.getElementById("doctor-status").textContent = "Doctor status unavailable";
    }
  }, 2000);
}

async function runDoctor() {
  const button = document.getElementById("doctor-run-button");
  button.disabled = true;
  document.getElementById("doctor-button-label").textContent = "Starting…";
  document.getElementById("doctor-status").textContent = "Starting Doctor";
  setDoctorHealth("running");
  setDoctorBullets(["Starting the local health check."]);
  try {
    const snapshot = await request("/api/doctor", { method: "POST", body: "{}" });
    render(snapshot);
    scheduleDoctorPolling();
  } catch (error) {
    button.disabled = false;
    document.getElementById("doctor-button-label").textContent = "Run Doctor";
    setDoctorHealth("failed");
    setDoctorBullets([error.message]);
    document.getElementById("doctor-status").textContent = "Doctor could not start";
  }
}

function openSettings() {
  if (!state.snapshot) return;
  const settings = state.snapshot.settings;
  document.getElementById("refresh-seconds").value = String(settings.refresh_seconds);
  document.getElementById("settings-message").textContent = "";
  document.getElementById("settings-dialog").showModal();
}

async function saveSettings() {
  const message = document.getElementById("settings-message");
  const button = document.getElementById("save-settings");
  button.disabled = true;
  message.textContent = "Saving…";
  try {
    await request("/api/settings", {
      method: "POST",
      body: JSON.stringify({
        refresh_seconds: Number(document.getElementById("refresh-seconds").value),
      }),
    });
    document.getElementById("settings-dialog").close();
    render(await request("/api/snapshot"));
  } catch (error) {
    message.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

document.querySelectorAll(".filter-tab").forEach((button) => {
  button.addEventListener("click", () => {
    setFilter(button.dataset.filter);
  });
});

document.querySelectorAll(".metric").forEach((button) => {
  button.addEventListener("click", () => setFilter(button.dataset.filter, true));
});

document.getElementById("refresh-button").addEventListener("click", refreshNow);
document.getElementById("doctor-run-button").addEventListener("click", runDoctor);
document.getElementById("settings-button").addEventListener("click", openSettings);
document.getElementById("save-settings").addEventListener("click", saveSettings);

async function start() {
  schedulePolling();
  try {
    render(await request("/api/snapshot"));
  } catch (error) {
    document.getElementById("live-label").textContent = "Local collector unavailable";
    document.getElementById("task-list").replaceChildren(element("div", "empty-tasks", "Mission Control could not reach its local collector."));
  }
}

start();
