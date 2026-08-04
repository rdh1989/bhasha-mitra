/******************************************************************************
 *
 * Bhasha Mitra
 * API Service
 *
 * Description:
 * Centralized REST API Client
 *
 * Author  : Team 1 & Team 4
 * Version : 1.0.0
 *
 *****************************************************************************/

class ApiService {

    constructor() {

        /*
         * If frontend and backend are served by the same FastAPI application,
         * keep this empty.
         *
         * Example:
         * ""
         *
         * Separate backend:
         * "http://localhost:8000/api"
         */

        this.baseUrl = "";

        this.defaultHeaders = {

            "Accept": "application/json"

        };

        this.timeout = 300000; // 5 Minutes

    }

    /*=========================================================================
        Internal Request
    =========================================================================*/

    async request(endpoint, options = {}) {

        const controller = new AbortController();

        const timer = setTimeout(() => {

            controller.abort();

        }, this.timeout);

        try {

            const response = await fetch(

                this.baseUrl + endpoint,

                {
                    ...options,

                    headers: {
                        ...this.defaultHeaders,
                        ...(options.headers || {})
                    },

                    signal: controller.signal

                }

            );

            clearTimeout(timer);

            const contentType = response.headers.get("content-type");

            let data = null;

            if (contentType &&
                contentType.includes("application/json")) {

                data = await response.json();

            }
            else {

                data = await response.text();

            }

            if (!response.ok) {

                throw {

                    status: response.status,

                    message: data.detail || data.message || "Request Failed",

                    response: data

                };

            }

            return data;

        }
        catch (error) {

            if (error.name === "AbortError") {

                throw {

                    status: 408,

                    message: "Request Timed Out"

                };

            }

            throw error;

        }

    }

    /*=========================================================================
        GET
    =========================================================================*/

    async get(endpoint) {

        return this.request(endpoint, {

            method: "GET"

        });

    }

    /*=========================================================================
        POST
    =========================================================================*/

    async post(endpoint, payload = {}) {

        return this.request(endpoint, {

            method: "POST",

            headers: {

                "Content-Type": "application/json"

            },

            body: JSON.stringify(payload)

        });

    }

    /*=========================================================================
        PUT
    =========================================================================*/

    async put(endpoint, payload = {}) {

        return this.request(endpoint, {

            method: "PUT",

            headers: {

                "Content-Type": "application/json"

            },

            body: JSON.stringify(payload)

        });

    }

    /*=========================================================================
        DELETE
    =========================================================================*/

    async delete(endpoint) {

        return this.request(endpoint, {

            method: "DELETE"

        });

    }

    /*=========================================================================
        File Upload
    =========================================================================*/

    async upload(endpoint, formData) {

        return this.request(endpoint, {

            method: "POST",

            body: formData

        });

    }

    /*=========================================================================
        Download File
    =========================================================================*/

    async download(endpoint) {

        const response = await fetch(this.baseUrl + endpoint);

        if (!response.ok) {

            throw new Error("Download Failed");

        }

        return response.blob();

    }

}

/*=============================================================================
    Global Instance
=============================================================================*/

window.Api = new ApiService();