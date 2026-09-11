(function () {
    "use strict";

    function toggleWishlist(btn) {
        var packageId = btn.getAttribute("data-package-id");
        fetch("/tours/" + packageId + "/wishlist/toggle", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({jsonrpc: "2.0", method: "call", params: {}}),
        }).then(function (r) { return r.json(); }).then(function (data) {
            if (!data.result) {
                window.location.href = "/web/login?redirect=" + encodeURIComponent(window.location.pathname);
                return;
            }
            var wishlisted = !!data.result.wishlisted;
            btn.classList.toggle("kt_wishlist_active", wishlisted);
            btn.setAttribute("aria-pressed", wishlisted ? "true" : "false");
        });
    }

    function initWishlistButtons() {
        document.querySelectorAll(".kt_wishlist_btn").forEach(function (btn) {
            if (btn.dataset.wishlistInit) { return; }
            btn.dataset.wishlistInit = "1";
            btn.addEventListener("click", function (ev) {
                ev.preventDefault();
                ev.stopPropagation();
                toggleWishlist(btn);
            });
        });
    }

    // This file loads inside Odoo's "lazy" asset bundle, which typically
    // finishes fetching well after DOMContentLoaded has already fired -
    // waiting on that event here would mean the listener never attaches.
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initWishlistButtons);
    } else {
        initWishlistButtons();
    }
})();
