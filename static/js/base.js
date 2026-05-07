// Runs after the HTML page fully loads.
document.addEventListener("DOMContentLoaded", function () {

    // Gets the nav sidebar toggle button, sidebar element, and page body.
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("sidebar");
    const body = document.body;

    // Key used to save the nav sidebar state in localStorage.
    const sidebarStorageKey = "spendsenseSidebarState";

    // Restores the user's previous nav sidebar state when the page reloads.
    const savedState = localStorage.getItem(sidebarStorageKey);

    // If the nav sidebar was previously closed, keep it closed.
    if (savedState === "closed") {
        sidebar.classList.remove("open");
        body.classList.remove("sidebar-open");

    } else {

        // Default behavior keeps the nav sidebar open.
        sidebar.classList.add("open");
        body.classList.add("sidebar-open");
    }

    // Handles nav sidebar open/close toggling.
    if (sidebarToggle && sidebar) {

        sidebarToggle.addEventListener("click", function () {

            // Toggles nav sidebar visibility classes.
            sidebar.classList.toggle("open");
            body.classList.toggle("sidebar-open");

            // Saves the current nav sidebar state in localStorage.
            if (sidebar.classList.contains("open")) {
                localStorage.setItem(sidebarStorageKey, "open");

            } else {
                localStorage.setItem(sidebarStorageKey, "closed");
            }
        });
    }
});