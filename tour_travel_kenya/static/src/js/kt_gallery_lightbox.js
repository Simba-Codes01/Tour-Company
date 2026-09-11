(function () {
    "use strict";

    function initGalleryLightbox() {
        var container = document.querySelector("[data-kt-gallery]");
        if (!container) { return; }
        var images = JSON.parse(container.getAttribute("data-kt-gallery") || "[]");
        if (!images.length) { return; }

        var modalImg = document.getElementById("kt_gallery_modal_img");
        var current = 0;

        function show(index) {
            current = (index + images.length) % images.length;
            if (modalImg) { modalImg.setAttribute("src", images[current]); }
        }

        container.querySelectorAll("[data-kt-gallery-index]").forEach(function (thumb) {
            thumb.addEventListener("click", function () {
                show(parseInt(thumb.getAttribute("data-kt-gallery-index"), 10));
            });
        });

        var prevBtn = document.getElementById("kt_gallery_prev");
        var nextBtn = document.getElementById("kt_gallery_next");
        if (prevBtn) { prevBtn.addEventListener("click", function () { show(current - 1); }); }
        if (nextBtn) { nextBtn.addEventListener("click", function () { show(current + 1); }); }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initGalleryLightbox);
    } else {
        initGalleryLightbox();
    }
})();
