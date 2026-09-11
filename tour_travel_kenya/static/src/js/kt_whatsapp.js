(function () {
    "use strict";

    function initWhatsappButton() {
        var btn = document.getElementById("kt_whatsapp_button");
        if (!btn) { return; }
        var phone = (btn.getAttribute("data-phone") || "").replace(/[^\d]/g, "");
        if (!phone) {
            btn.hidden = true;
            return;
        }
        var message = "Hi! I have a question about your Kenya tours.";
        btn.href = "https://wa.me/" + phone + "?text=" + encodeURIComponent(message);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initWhatsappButton);
    } else {
        initWhatsappButton();
    }
})();
