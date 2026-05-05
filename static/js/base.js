document.addEventListener("DOMContentLoaded", function () {
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("sidebar");
    const body = document.body;

    const sidebarStorageKey = "spendsenseSidebarState";

    // Restore sidebar state on page load
    const savedState = localStorage.getItem(sidebarStorageKey);

    if (savedState === "closed") {
        sidebar.classList.remove("open");
        body.classList.remove("sidebar-open");
    } else {
        // default = open
        sidebar.classList.add("open");
        body.classList.add("sidebar-open");
    }

    // Save state when toggled
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener("click", function () {
            sidebar.classList.toggle("open");
            body.classList.toggle("sidebar-open");

            if (sidebar.classList.contains("open")) {
                localStorage.setItem(sidebarStorageKey, "open");
            } else {
                localStorage.setItem(sidebarStorageKey, "closed");
            }
        });
    }
});