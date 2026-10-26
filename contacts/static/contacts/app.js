// Behaviour shared by every page: the light/dark theme switch and toast notifications.
(function () {
  // --- Theme -------------------------------------------------------------
  // The saved theme is applied by a tiny inline script in <head> (before the page is drawn);
  // here we only handle the toggle button.
  const toggle = document.querySelector("[data-theme-toggle]");

  function updateToggle() {
    const dark = document.documentElement.dataset.bsTheme === "dark";
    toggle.querySelector("i").className = dark ? "bi bi-sun" : "bi bi-moon-stars";
    toggle.setAttribute("aria-label", dark ? "Włącz jasny motyw" : "Włącz ciemny motyw");
  }

  toggle.addEventListener("click", () => {
    const theme = document.documentElement.dataset.bsTheme === "dark" ? "light" : "dark";
    document.documentElement.dataset.bsTheme = theme;
    try {
      localStorage.setItem("theme", theme);
    } catch (error) {
      // storage can be blocked (e.g. private mode) - the theme then lasts until the page reloads
    }
    updateToggle();
    document.dispatchEvent(new CustomEvent("themechange")); // lets the charts redraw in new colors
  });
  updateToggle();

  // --- Toasts ------------------------------------------------------------
  const ICONS = {
    success: "bi-check-circle-fill text-success",
    info: "bi-info-circle-fill text-info",
    warning: "bi-exclamation-triangle-fill text-warning",
    error: "bi-x-circle-fill text-danger",
  };
  const container = document.getElementById("toasts");
  const template = document.getElementById("toast-template");

  function showToast(text, level) {
    const toast = template.content.firstElementChild.cloneNode(true);
    toast.querySelector("[data-toast-icon]").className = `bi ${ICONS[level] || ICONS.info}`;
    toast.querySelector("[data-toast-text]").textContent = text;
    container.append(toast);
    toast.addEventListener("hidden.bs.toast", () => toast.remove());
    new bootstrap.Toast(toast, { delay: 4000 }).show();
  }

  // Messages added by Django views (django.contrib.messages)
  document.querySelectorAll("#django-messages li").forEach((item) => {
    showToast(item.textContent, item.dataset.level);
  });

  // Messages sent by htmx responses in the HX-Trigger header: {"showMessage": {"text": ..., "level": ...}}
  document.body.addEventListener("showMessage", (event) => {
    showToast(event.detail.text, event.detail.level);
  });
})();