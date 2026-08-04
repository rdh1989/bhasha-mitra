/******************************************************************************
 *
 * Bhasha Mitra
 * Dashboard Controller
 *
 * Description:
 * Handles Dashboard initialization, statistics, system health,
 * recent activity and dashboard refresh.
 *
 * Author  : Team 4
 * Version : 1.0.0
 *
 *****************************************************************************/

class DashboardController {

    constructor() {

        this.stats = {

            totalVideos: document.getElementById("totalVideos"),
            supportedLanguages: document.getElementById("supportedLanguages"),
            translationAccuracy: document.getElementById("translationAccuracy"),
            activeJobs: document.getElementById("activeJobs")

        };

        this.initialize();

    }

    /*=========================================================================
        Initialize
    =========================================================================*/

    async initialize() {

        try {

            App.showLoading("Loading Dashboard...");

            await this.loadDashboard();

            console.log("Dashboard Loaded");

        }
        catch (error) {

            console.error(error);

            App.showToast(
                error.message || "Unable to load dashboard",
                "error"
            );

        }
        finally {

            App.hideLoading();

        }

    }

    /*=========================================================================
        Dashboard Data
    =========================================================================*/

    async loadDashboard() {

        /*
         * Current implementation:
         * Uses values already rendered by Jinja.
         *
         * Future:
         * Replace with
         *
         * const data = await Api.get("/api/dashboard");
         * this.updateDashboard(data);
         */

        this.animateCounters();

    }

    /*=========================================================================
        Update Dashboard
    =========================================================================*/

    updateDashboard(data) {

        if (!data)
            return;

        this.updateText(

            this.stats.totalVideos,

            data.total_videos

        );

        this.updateText(

            this.stats.supportedLanguages,

            data.supported_languages

        );

        this.updateText(

            this.stats.translationAccuracy,

            data.translation_accuracy + "%"

        );

        this.updateText(

            this.stats.activeJobs,

            data.active_jobs

        );

    }

    /*=========================================================================
        Helpers
    =========================================================================*/

    updateText(element, value) {

        if (!element)
            return;

        element.textContent = value;

    }

    /*=========================================================================
        Counter Animation
    =========================================================================*/

    animateCounters() {

        const counters = [

            this.stats.totalVideos,

            this.stats.supportedLanguages,

            this.stats.translationAccuracy,

            this.stats.activeJobs

        ];

        counters.forEach(counter => {

            if (!counter)
                return;

            const value = counter.textContent;

            const numeric = parseInt(value);

            if (isNaN(numeric))
                return;

            let current = 0;

            const increment = Math.max(
                1,
                Math.ceil(numeric / 40)
            );

            const timer = setInterval(() => {

                current += increment;

                if (current >= numeric) {

                    current = numeric;

                    clearInterval(timer);

                }

                if (value.includes("%")) {

                    counter.textContent = current + "%";

                }
                else {

                    counter.textContent = current;

                }

            }, 20);

        });

    }

    /*=========================================================================
        Refresh
    =========================================================================*/

    async refresh() {

        try {

            App.showLoading("Refreshing...");

            await this.loadDashboard();

            App.showToast("Dashboard Updated");

        }
        catch (error) {

            console.error(error);

            App.showToast(
                "Refresh Failed",
                "error"
            );

        }
        finally {

            App.hideLoading();

        }

    }

}

/*=============================================================================
    Initialize
=============================================================================*/

document.addEventListener("DOMContentLoaded", () => {

    window.Dashboard = new DashboardController();

});