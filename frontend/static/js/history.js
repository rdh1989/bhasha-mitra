/******************************************************************************
 *
 * Bhasha Mitra
 * History Controller
 *
 * Description:
 * Handles Translation History
 *
 * Author  : Team 4
 * Version : 1.0.0
 *
 *****************************************************************************/

class HistoryController {

    constructor() {

        this.tableBody = document.getElementById("historyTableBody");

        this.searchBox = document.getElementById("historySearch");

        this.statusFilter = document.getElementById("statusFilter");

        this.refreshButton = document.getElementById("refreshHistory");

        this.currentPage = 1;

        this.pageSize = 10;

        this.history = [];

        this.initialize();

    }

    /*=========================================================================
        Initialize
    =========================================================================*/

    async initialize() {

        this.registerEvents();

        await this.loadHistory();

    }

    /*=========================================================================
        Events
    =========================================================================*/

    registerEvents() {

        this.searchBox?.addEventListener(

            "input",

            () => this.filterHistory()

        );

        this.statusFilter?.addEventListener(

            "change",

            () => this.filterHistory()

        );

        this.refreshButton?.addEventListener(

            "click",

            () => this.loadHistory()

        );

    }

    /*=========================================================================
        Load History
    =========================================================================*/

    async loadHistory() {

        try {

            App.showLoading("Loading History...");

            /*
            this.history =
                await Api.get("/api/history");
            */

            this.history = this.demoData();

            this.render(this.history);

        }
        catch (error) {

            console.error(error);

            App.showToast(

                "Unable to load history",

                "error"

            );

        }
        finally {

            App.hideLoading();

        }

    }

    /*=========================================================================
        Render Table
    =========================================================================*/

    render(records) {

        if (!this.tableBody)
            return;

        this.tableBody.innerHTML = "";

        if (records.length === 0) {

            this.tableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center">
                        No Records Found
                    </td>
                </tr>
            `;

            return;

        }

        records.forEach(record => {

            this.tableBody.insertAdjacentHTML(

                "beforeend",

                `
                <tr>

                    <td>${record.file}</td>

                    <td>${record.source}</td>

                    <td>${record.target}</td>

                    <td>${record.date}</td>

                    <td>

                        <span class="badge badge-success">

                            ${record.status}

                        </span>

                    </td>

                    <td>${record.duration}</td>

                    <td>

                        <button
                            class="btn btn-secondary btn-download"
                            data-id="${record.id}">

                            <i class="fa-solid fa-download"></i>

                        </button>

                        <button
                            class="btn btn-danger btn-delete"
                            data-id="${record.id}">

                            <i class="fa-solid fa-trash"></i>

                        </button>

                    </td>

                </tr>
                `

            );

        });

        this.registerRowEvents();

    }

    /*=========================================================================
        Search + Filter
    =========================================================================*/

    filterHistory() {

        const keyword =

            this.searchBox?.value.toLowerCase() || "";

        const status =

            this.statusFilter?.value || "";

        let filtered = this.history.filter(item => {

            const matchesSearch =

                item.file.toLowerCase().includes(keyword);

            const matchesStatus =

                status === "" ||

                item.status === status;

            return matchesSearch && matchesStatus;

        });

        this.render(filtered);

    }

    /*=========================================================================
        Row Buttons
    =========================================================================*/

    registerRowEvents() {

        document.querySelectorAll(".btn-download")

            .forEach(button => {

                button.onclick = () => {

                    this.download(

                        button.dataset.id

                    );

                };

            });

        document.querySelectorAll(".btn-delete")

            .forEach(button => {

                button.onclick = () => {

                    this.delete(

                        button.dataset.id

                    );

                };

            });

    }

    /*=========================================================================
        Download
    =========================================================================*/

    async download(id) {

        try {

            /*
            const blob =
                await Api.download(
                    `/api/history/${id}/video`
                );
            */

            App.showToast(

                "Download Started"

            );

        }
        catch (error) {

            console.error(error);

        }

    }

    /*=========================================================================
        Delete
    =========================================================================*/

    async delete(id) {

        if (!confirm(

            "Delete this translation?"

        ))
            return;

        try {

            /*
            await Api.delete(
                `/api/history/${id}`
            );
            */

            this.history = this.history.filter(

                item => item.id != id

            );

            this.render(this.history);

            App.showToast(

                "History Deleted"

            );

        }
        catch (error) {

            console.error(error);

            App.showToast(

                "Delete Failed",

                "error"

            );

        }

    }

    /*=========================================================================
        Demo
    =========================================================================*/

    demoData() {

        return [

            {

                id:1,

                file:"Meeting.mp4",

                source:"English",

                target:"Marathi",

                date:"21-Jul-2026",

                duration:"08:25",

                status:"Completed"

            },

            {

                id:2,

                file:"Training.mp4",

                source:"Hindi",

                target:"Tamil",

                date:"20-Jul-2026",

                duration:"15:12",

                status:"Completed"

            },

            {

                id:3,

                file:"Lecture.mp4",

                source:"English",

                target:"Gujarati",

                date:"18-Jul-2026",

                duration:"42:10",

                status:"Completed"

            }

        ];

    }

}

document.addEventListener(

    "DOMContentLoaded",

    () => {

        window.History =

            new HistoryController();

    }

);