const form = document.querySelector("#applicationForm");
const previewButton = document.querySelector("#previewButton");
const generateButton = document.querySelector("#generateButton");
const projectList = document.querySelector("#projectList");
const emptyState = document.querySelector("#emptyState");
const inferredPanel = document.querySelector("#inferred");
const statusLine = document.querySelector("#status");
const successPanel = document.querySelector("#successPanel");

let hasPreview = false;

function csv(value) {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function selectedProjects() {
  const boxes = [...projectList.querySelectorAll('input[type="checkbox"]')];
  return {
    included: boxes.filter((box) => box.checked).map((box) => box.value),
    excluded: boxes.filter((box) => !box.checked).map((box) => box.value),
  };
}

function applicationData(useProjectChoices = false) {
  const projectChoices = useProjectChoices && hasPreview
    ? selectedProjects()
    : { included: [], excluded: [] };
  const chosenCount = projectChoices.included.length;
  return {
    office: document.querySelector("#office").value,
    position: document.querySelector("#position").value,
    job_description: document.querySelector("#jobDescription").value,
    software: csv(document.querySelector("#software").value),
    skills: csv(document.querySelector("#skills").value),
    focus: csv(document.querySelector("#focus").value),
    project_limit: chosenCount || Number(document.querySelector("#projectLimit").value),
    include_projects: projectChoices.included,
    exclude_projects: projectChoices.excluded,
    include_hobbies: document.querySelector("#includeHobbies").checked,
    hobby_categories: [],
    hobby_item_limit: 5,
  };
}

function setBusy(isBusy, message) {
  previewButton.disabled = isBusy;
  generateButton.disabled = isBusy;
  statusLine.classList.remove("error");
  statusLine.textContent = message;
}

function setError(message) {
  statusLine.classList.add("error");
  statusLine.textContent = message;
}

async function api(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.json().catch(() => ({ error: "Unexpected server response." }));
  if (!response.ok) throw new Error(body.error || "Request failed.");
  return body;
}

function inferredSummary(inferred) {
  const groups = Object.entries(inferred)
    .filter(([, items]) => items.length)
    .map(([name, items]) => `${name}: ${items.join(", ")}`);
  return groups.length ? `Detected from the vacancy · ${groups.join(" / ")}` : "No additional known terms were detected. Your manual fields still guide the ranking.";
}

function renderProjects(data) {
  emptyState.hidden = true;
  inferredPanel.hidden = false;
  inferredPanel.textContent = inferredSummary(data.inferred);
  projectList.innerHTML = "";

  data.projects.forEach((project) => {
    const card = document.createElement("label");
    card.className = `project-card${project.selected ? " is-selected" : ""}`;
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = project.id;
    checkbox.checked = project.selected;
    checkbox.addEventListener("change", () => {
      card.classList.toggle("is-selected", checkbox.checked);
      const count = selectedProjects().included.length;
      statusLine.textContent = `${count} project${count === 1 ? "" : "s"} selected.`;
    });

    const id = document.createElement("span");
    id.className = "project-id";
    id.textContent = project.id;

    const content = document.createElement("div");
    const title = document.createElement("div");
    title.className = "project-title";
    title.textContent = project.title;
    const reasons = document.createElement("div");
    reasons.className = "project-reasons";
    reasons.textContent = project.reasons.length ? project.reasons.join(" · ") : "Library match";
    content.append(title, reasons);

    const score = document.createElement("span");
    score.className = "project-score";
    score.textContent = project.score.toFixed(1);
    card.append(checkbox, id, content, score);
    projectList.append(card);
  });
  hasPreview = true;
}

async function preview() {
  setBusy(true, "Ranking projects…");
  successPanel.hidden = true;
  try {
    const data = await api("/api/preview", applicationData(false));
    renderProjects(data);
    const count = selectedProjects().included.length;
    setBusy(false, `${count} projects selected. Review the list or generate now.`);
  } catch (error) {
    setBusy(false, "Ready.");
    setError(error.message);
  }
}

previewButton.addEventListener("click", preview);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = applicationData(true);
  if (hasPreview && payload.include_projects.length === 0) {
    setError("Select at least one project.");
    return;
  }
  setBusy(true, "Generating PDFs… this can take a moment.");
  successPanel.hidden = true;
  try {
    const result = await api("/api/generate", payload);
    document.querySelector("#portfolioDownload").href = result.downloads.portfolio;
    document.querySelector("#portfolioHtmlDownload").href = result.downloads.portfolio_html;
    document.querySelector("#cvDownload").href = result.downloads.cv;
    document.querySelector("#selectionDownload").href = result.downloads.selection;
    document.querySelector("#applicationDownload").href = result.downloads.application;
    document.querySelector("#outputPath").textContent = result.output_directory;
    successPanel.hidden = false;
    successPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    setBusy(false, "Application package generated successfully.");
  } catch (error) {
    setBusy(false, "Ready.");
    setError(error.message);
  }
});
