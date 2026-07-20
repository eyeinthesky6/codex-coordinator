document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", async () => {
    const source = document.getElementById(button.dataset.copy);
    if (!source) return;

    try {
      await navigator.clipboard.writeText(source.textContent.trim());
      const previous = button.textContent;
      button.textContent = "Copied";
      const status = document.getElementById("copy-status");
      if (status) status.textContent = "Copied to clipboard";
      setTimeout(() => { button.textContent = previous; }, 1600);
    } catch (_) {
      window.getSelection().selectAllChildren(source);
    }
  });
});

const demoTabs = [...document.querySelectorAll("[data-demo-tab]")];

function showDemo(tab) {
  demoTabs.forEach((candidate) => {
    const selected = candidate === tab;
    const panel = document.getElementById(candidate.dataset.demoTab);
    candidate.classList.toggle("active", selected);
    candidate.setAttribute("aria-selected", String(selected));
    candidate.tabIndex = selected ? 0 : -1;
    if (panel) panel.hidden = !selected;
  });
}

demoTabs.forEach((tab, index) => {
  tab.addEventListener("click", () => showDemo(tab));
  tab.addEventListener("keydown", (event) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const direction = event.key === "ArrowRight" ? 1 : -1;
    const next = demoTabs[(index + direction + demoTabs.length) % demoTabs.length];
    showDemo(next);
    next.focus();
  });
});
