import { html } from "/assets/vendor/arrow-core.js";
import { hideSidebar, upperFirst } from "/assets/js/utils.js";

const MENU_ITEMS = {
  home: [
    { name: "Home", link: "/", icon: "bi-house-fill" },
  ],
  recordings: [
    { name: "Dashcam Routes", link: "/dashcam_routes", icon: "bi-camera-reels" },
    { name: "Screen Recordings", link: "/screen_recordings", icon: "bi-record-circle" },
  ],
  tools: [
    { name: "Toggles", link: "/device_settings", icon: "bi-toggle-on" },
    { name: "Download Speed Limits", link: "/download_speed_limits", icon: "bi-download" },
    { name: "Error Logs", link: "/manage_error_logs", icon: "bi-exclamation-triangle" },
    { name: "Galaxy", link: "/galaxy", icon: "bi-globe2" },
    { name: "Long Maneuvers", link: "/longitudinal_maneuvers", icon: "bi-signpost-split" },
    { name: "Maps", link: "/manage_maps", icon: "bi-map" },
    { name: "Navigation Keys", link: "/manage_navigation_keys", icon: "bi-key-fill" },
    { name: "Model Manager", link: "/manage_models", icon: "bi-cpu" },
    { name: "Plots", link: "/plots", icon: "bi-graph-up-arrow" },
    { name: "Testing Ground", link: "/testing_ground", icon: "bi-bezier2" },
    { name: "Troubleshoot", link: "/troubleshoot", icon: "bi-tools" },
    { name: "Theme Maker", link: "/theme_maker", icon: "bi-palette-fill" },
    { name: "Tmux Log", link: "/manage_tmux", icon: "bi-terminal" },
    { name: "Backup and Restore", link: "/manage_toggles", icon: "bi-arrow-repeat" },
    { name: "Software", link: "/manage_updates", icon: "bi-arrow-up-circle" },
    { name: "Vehicle Features", link: "/vehicle_features", icon: "bi-car-front" },
  ],
};

function matchesPath(currentPath, link) {
  if (link === "/") return currentPath === "/";
  return currentPath === link || currentPath.startsWith(`${link}/`);
}

function buildSectionMarkup(section, links, currentPath) {
  const linksMarkup = links.map((link) => {
    const active = matchesPath(currentPath, link.link) ? "active" : "";
    return `
      <li class="${active}">
        <a class="menu-item-link" href="${link.link}">
          <i class="bi ${link.icon}"></i>
          <span>${upperFirst(link.name)}</span>
        </a>
      </li>
    `;
  }).join("");

  return `
    <div class="sidebar_widget">
      <ul class="menu_section">
        <li>
          <span class="section-title">${upperFirst(section)}</span>
          <ul id="${section}">
            ${linksMarkup}
          </ul>
        </li>
      </ul>
    </div>
  `;
}

function bindSidebarHandlers() {
  const menuButton = document.getElementById("menu_button");
  const underlay = document.getElementById("sidebarUnderlay");

  if (!menuButton || !underlay) return;

  if (!window.__thePondSidebarMenuBound) {
    window.__thePondSidebarMenuBound = true;
    menuButton.addEventListener("click", () => {
      const sidebar = document.getElementById("sidebar");
      const currentUnderlay = document.getElementById("sidebarUnderlay");
      if (!sidebar || !currentUnderlay) return;
      sidebar.classList.toggle("visible");
      currentUnderlay.classList.toggle("hidden");
    });
  }

  underlay.onclick = hideSidebar;

  document.querySelectorAll("#sidebar a.menu-item-link").forEach((anchor) => {
    if (anchor.dataset.boundClick === "1") return;
    anchor.dataset.boundClick = "1";
    anchor.addEventListener("click", (event) => {
      if (event.defaultPrevented) return;
      if (event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

      event.preventDefault();
      const href = anchor.getAttribute("href") || "/";
      const navigate = window.__thePondNavigate;
      if (typeof navigate === "function") {
        navigate(href);
      } else {
        window.location.assign(href);
      }
      hideSidebar();
      window.scrollTo(0, 0);
    });
  });
}

function renderSidebarIntoShell(currentPath) {
  const shell = document.getElementById("sidebar_shell");
  if (!shell) return;

  const activePath = currentPath || window.location.pathname;
  const sectionsMarkup = Object.entries(MENU_ITEMS)
    .map(([section, links]) => buildSectionMarkup(section, links, activePath))
    .join("");

  shell.innerHTML = `
    <div id="sidebarUnderlay" class="hidden"></div>
    <div id="sidebar" class="sidebar">
      <div>
        <div class="title">
          <img class="logo" src="/assets/images/main_logo.png" alt="Galaxy logo" />
          <div class="title_text sidebar_header">
            <p>Galaxy</p>
          </div>
        </div>
        <hr />
        ${sectionsMarkup}
      </div>
    </div>
  `;

  bindSidebarHandlers();
}

export function Sidebar(currentPath) {
  setTimeout(() => renderSidebarIntoShell(currentPath), 0);
  return html`<div id="sidebar_shell"></div>`;
}
