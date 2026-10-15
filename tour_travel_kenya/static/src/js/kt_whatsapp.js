(function () {
    "use strict";

    var DEFAULT_MESSAGE = "Hi! I have a question about your Kenya tours.";

    function wireButton(btn) {
        var phone = (btn.getAttribute("data-phone") || "").replace(/[^\d]/g, "");
        if (!phone) {
            btn.hidden = true;
            return;
        }
        var message = btn.getAttribute("data-message") || DEFAULT_MESSAGE;
        btn.href = "https://wa.me/" + phone + "?text=" + encodeURIComponent(message);
    }

    function initWhatsappButtons() {
        // .kt_whatsapp_link covers every WhatsApp CTA on the page (the floating
        // button plus any inline "Message us on WhatsApp" buttons in forms) -
        // each can carry its own data-message for context-specific greetings.
        document.querySelectorAll(".kt_whatsapp_link").forEach(wireButton);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initWhatsappButtons);
    } else {
        initWhatsappButtons();
    }
})();
