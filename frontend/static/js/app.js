/******************************************************************************
 *
 * Bhasha Mitra
 * Global Application Controller
 *
 * Description:
 * Initializes common UI behaviour used across all pages.
 *
 * Author  : Team 4
 * Version : 1.0.0
 *
 *****************************************************************************/

class BhashaMitraApp {

    constructor() {

        this.sidebar = document.querySelector(".sidebar");
        this.sidebarToggle = document.getElementById("sidebarToggle");

        this.initialize();

    }

    initialize() {

        this.initializeSidebar();
        this.initializeNavigation();
        this.initializeTooltips();

        console.log("Bhasha Mitra UI Initialized");

    }

    /*=========================================================================
        Sidebar
    =========================================================================*/

    initializeSidebar() {

        if (!this.sidebarToggle || !this.sidebar)
            return;

        this.sidebarToggle.addEventListener("click", () => {

            if (window.innerWidth <= 992) {

                this.sidebar.classList.toggle("open");

            }
            else {

                this.sidebar.classList.toggle("collapsed");

            }

        });

        document.addEventListener("click", (event) => {

            if (window.innerWidth > 992)
                return;

            const clickedInsideSidebar =
                this.sidebar.contains(event.target);

            const clickedToggle =
                this.sidebarToggle.contains(event.target);

            if (!clickedInsideSidebar && !clickedToggle) {

                this.sidebar.classList.remove("open");

            }

        });

    }

    /*=========================================================================
        Navigation
    =========================================================================*/

    initializeNavigation() {

        const currentPath = window.location.pathname;

        document.querySelectorAll(".nav-item").forEach(link => {

            link.classList.remove("active");

            const href = link.getAttribute("href");

            if (href === currentPath) {

                link.classList.add("active");

            }

        });

    }

    /*=========================================================================
        Tooltips (Future Ready)
    =========================================================================*/

    initializeTooltips() {

        document.querySelectorAll("[data-tooltip]").forEach(item => {

            item.title = item.dataset.tooltip;

        });

    }

    /*=========================================================================
        Loading Overlay
    =========================================================================*/

    showLoading(message = "Loading...") {

        let overlay = document.getElementById("loadingOverlay");

        if (!overlay) {

            overlay = document.createElement("div");

            overlay.id = "loadingOverlay";

            overlay.innerHTML = `
                <div class="loading-box">
                    <div class="spinner"></div>
                    <p>${message}</p>
                </div>
            `;

            Object.assign(overlay.style, {
                position: "fixed",
                inset: "0",
                background: "rgba(255,255,255,.75)",
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                zIndex: "9999"
            });

            document.body.appendChild(overlay);

        }

    }

    hideLoading() {

        const overlay = document.getElementById("loadingOverlay");

        if (overlay) {

            overlay.remove();

        }

    }

    /*=========================================================================
        Toast Notification
    =========================================================================*/

    showToast(message, type = "success") {

        const toast = document.createElement("div");

        toast.className = `toast ${type}`;

        toast.textContent = message;

        Object.assign(toast.style, {

            position: "fixed",

            top: "25px",

            right: "25px",

            padding: "14px 20px",

            borderRadius: "12px",

            color: "#fff",

            fontWeight: "600",

            zIndex: "9999",

            background:
                type === "success"
                    ? "#22C55E"
                    : type === "error"
                        ? "#EF4444"
                        : "#3B82F6"

        });

        document.body.appendChild(toast);

        setTimeout(() => {

            toast.remove();

        }, 3000);

    }

}

/*=============================================================================
    Global App
=============================================================================*/

window.App = new BhashaMitraApp();