(function () {
    "use strict";

    var STORAGE_KEY = "kt_theme";

    function storeTheme(theme) {
        try {
            window.localStorage.setItem(STORAGE_KEY, theme);
        } catch (e) {
            // localStorage unavailable (private mode, etc.) - theme just won't persist.
        }
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute("data-kt-theme", theme);
        var toggle = document.getElementById("kt_theme_toggle");
        if (toggle) {
            toggle.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
        }
    }

    function initThemeToggle() {
        var toggle = document.getElementById("kt_theme_toggle");
        if (!toggle) {
            return;
        }
        var current = document.documentElement.getAttribute("data-kt-theme") || "light";
        toggle.setAttribute("aria-pressed", current === "dark" ? "true" : "false");

        toggle.addEventListener("click", function () {
            var next = document.documentElement.getAttribute("data-kt-theme") === "dark" ? "light" : "dark";
            applyTheme(next);
            storeTheme(next);
        });
    }

    // This file loads inside Odoo's "lazy" asset bundle, which typically
    // finishes fetching well after DOMContentLoaded has already fired -
    // waiting on that event here would mean the listener never attaches.
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initThemeToggle);
    } else {
        initThemeToggle();
    }
})();
