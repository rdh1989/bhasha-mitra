/******************************************************************************
 *
 * Bhasha Mitra
 * Upload Controller
 *
 * Description:
 * Handles video upload workflow
 *
 * Author  : Team 4
 * Version : 1.0.0
 *
 *****************************************************************************/

class UploadController {

    constructor() {

        this.fileInput = document.getElementById("videoFile");
        this.dropZone = document.getElementById("dropZone");
        this.uploadButton = document.getElementById("uploadButton");

        this.progressContainer = document.getElementById("uploadProgress");
        this.progressBar = document.getElementById("progressBar");
        this.progressText = document.getElementById("progressText");

        this.selectedFile = null;

        this.initialize();

    }

    /*=========================================================================
        Initialize
    =========================================================================*/

    initialize() {

        this.registerFileInput();
        this.registerDragDrop();
        this.registerUploadButton();

    }

    /*=========================================================================
        File Input
    =========================================================================*/

    registerFileInput() {

        if (!this.fileInput)
            return;

        this.fileInput.addEventListener("change", (event) => {

            const file = event.target.files[0];

            if (file) {

                this.handleFile(file);

            }

        });

    }

    /*=========================================================================
        Drag Drop
    =========================================================================*/

    registerDragDrop() {

        if (!this.dropZone)
            return;

        ["dragenter", "dragover"].forEach(eventName => {

            this.dropZone.addEventListener(eventName, (event) => {

                event.preventDefault();

                this.dropZone.classList.add("drag-active");

            });

        });

        ["dragleave", "drop"].forEach(eventName => {

            this.dropZone.addEventListener(eventName, () => {

                this.dropZone.classList.remove("drag-active");

            });

        });

        this.dropZone.addEventListener("drop", (event) => {

            event.preventDefault();

            if (event.dataTransfer.files.length > 0) {

                this.handleFile(event.dataTransfer.files[0]);

            }

        });

    }

    /*=========================================================================
        Upload Button
    =========================================================================*/

    registerUploadButton() {

        if (!this.uploadButton)
            return;

        this.uploadButton.addEventListener("click", () => {

            this.upload();

        });

    }

    /*=========================================================================
        Handle File
    =========================================================================*/

    handleFile(file) {

        if (!this.validateFile(file))
            return;

        this.selectedFile = file;

        App.showToast(

            `${file.name} selected`

        );

        const fileName = document.getElementById("selectedFileName");

        if (fileName) {

            fileName.textContent = file.name;

        }

    }

    /*=========================================================================
        Validation
    =========================================================================*/

    validateFile(file) {

        const allowedTypes = [

            "video/mp4",

            "video/x-matroska",

            "video/quicktime",

            "video/x-msvideo"

        ];

        if (!allowedTypes.includes(file.type)) {

            App.showToast(

                "Unsupported video format",

                "error"

            );

            return false;

        }

        const maxSize = 5 * 1024 * 1024 * 1024;

        if (file.size > maxSize) {

            App.showToast(

                "Maximum file size is 5 GB",

                "error"

            );

            return false;

        }

        return true;

    }

    /*=========================================================================
        Upload
    =========================================================================*/

    async upload() {

        if (!this.selectedFile) {

            App.showToast(

                "Please select a video",

                "error"

            );

            return;

        }

        try {

            this.showProgress();

            const formData = new FormData();

            formData.append(

                "video",

                this.selectedFile

            );

            /*
             * Future Backend Integration
             *
             * const response =
             *      await Api.upload(
             *          "/api/videos/upload",
             *          formData
             *      );
             */

            await this.simulateUpload();

            App.showToast(

                "Video uploaded successfully."

            );

        }
        catch (error) {

            console.error(error);

            App.showToast(

                "Upload Failed",

                "error"

            );

        }
        finally {

            this.hideProgress();

        }

    }

    /*=========================================================================
        Progress
    =========================================================================*/

    showProgress() {

        if (this.progressContainer) {

            this.progressContainer.style.display = "block";

        }

    }

    hideProgress() {

        if (this.progressContainer) {

            this.progressContainer.style.display = "none";

        }

    }

    updateProgress(value) {

        if (this.progressBar) {

            this.progressBar.style.width = value + "%";

        }

        if (this.progressText) {

            this.progressText.textContent = value + "%";

        }

    }

    /*=========================================================================
        Demo Upload
    =========================================================================*/

    async simulateUpload() {

        return new Promise(resolve => {

            let progress = 0;

            const timer = setInterval(() => {

                progress += 2;

                this.updateProgress(progress);

                if (progress >= 100) {

                    clearInterval(timer);

                    resolve();

                }

            }, 50);

        });

    }

}

/*=============================================================================
    Initialize
=============================================================================*/

document.addEventListener(

    "DOMContentLoaded",

    () => {

        window.Upload = new UploadController();

    }

);