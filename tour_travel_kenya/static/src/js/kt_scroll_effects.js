(function () {
    "use strict";

    var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function initReveal() {
        var targets = document.querySelectorAll(".kt_reveal");
        if (!targets.length) { return; }
        if (reduceMotion || !("IntersectionObserver" in window)) {
            targets.forEach(function (el) { el.classList.add("kt_reveal_visible"); });
            return;
        }
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add("kt_reveal_visible");
                    observer.unobserve(entry.target);
                }
            });
        }, {threshold: 0.15, rootMargin: "0px 0px -40px 0px"});
        targets.forEach(function (el) { observer.observe(el); });
    }

    function initParallax() {
        if (reduceMotion) { return; }
        var layer = document.querySelector("[data-kt-parallax]");
        if (!layer) { return; }
        var strength = parseFloat(layer.getAttribute("data-kt-parallax")) || 0.3;
        var section = layer.closest(".kt_hero_tall") || layer.parentElement;
        var ticking = false;

        function update() {
            ticking = false;
            // Stop moving the layer once its section has scrolled well out of
            // view - nothing to gain visually, and it saves a style write per
            // scroll tick for the rest of a long page.
            if (window.scrollY > section.offsetHeight + 200) { return; }
            layer.style.transform = "translateY(" + (window.scrollY * strength) + "px)";
        }

        function onScroll() {
            if (!ticking) {
                ticking = true;
                window.requestAnimationFrame(update);
            }
        }

        update();
        window.addEventListener("scroll", onScroll, {passive: true});
    }

    function initCountUp() {
        var targets = document.querySelectorAll("[data-kt-countup]");
        if (!targets.length) { return; }

        function animate(el) {
            var target = parseInt(el.getAttribute("data-kt-countup"), 10) || 0;
            var prefix = el.getAttribute("data-kt-countup-prefix") || "";
            var suffix = el.getAttribute("data-kt-countup-suffix") || "";
            if (reduceMotion || !target) {
                el.textContent = prefix + target + suffix;
                return;
            }
            var duration = 1200;
            var start = null;

            function step(timestamp) {
                if (start === null) { start = timestamp; }
                var progress = Math.min((timestamp - start) / duration, 1);
                var eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
                el.textContent = prefix + Math.round(target * eased) + suffix;
                if (progress < 1) {
                    window.requestAnimationFrame(step);
                }
            }
            window.requestAnimationFrame(step);
        }

        if (!("IntersectionObserver" in window)) {
            targets.forEach(animate);
            return;
        }
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    animate(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, {threshold: 0.5});
        targets.forEach(function (el) { observer.observe(el); });
    }

    function initStickyBookingBar() {
        var bookingCard = document.getElementById("kt_booking_card");
        var bar = document.querySelector(".kt_sticky_booking_bar");
        if (!bookingCard || !bar || !("IntersectionObserver" in window)) { return; }

        var observer = new IntersectionObserver(function (entries) {
            var entry = entries[0];
            // Only show once the visitor has scrolled past the booking card
            // (it left the top of the viewport) - not before reaching it.
            var scrolledPast = !entry.isIntersecting && entry.boundingClientRect.top < 0;
            bar.classList.toggle("kt_sticky_visible", scrolledPast);
        }, {threshold: 0});
        observer.observe(bookingCard);

        var jumpBtn = bar.querySelector("[data-kt-scroll-to-booking]");
        if (jumpBtn) {
            jumpBtn.addEventListener("click", function () {
                bookingCard.scrollIntoView({behavior: reduceMotion ? "auto" : "smooth", block: "center"});
            });
        }
    }

    function initHeaderScroll() {
        // Header is `position: sticky` (see SCSS), so it stays pinned at the
        // top once scrolled past rather than scrolling away - this just adds
        // a shadow and shrinks its padding once that happens, purely visual.
        var navLeft = document.querySelector(".kt_nav_left");
        var header = navLeft && navLeft.closest("header");
        if (!header) { return; }

        var threshold = 40;
        var ticking = false;

        function update() {
            ticking = false;
            header.classList.toggle("kt_header_scrolled", window.scrollY > threshold);
        }

        function onScroll() {
            if (!ticking) {
                ticking = true;
                window.requestAnimationFrame(update);
            }
        }

        update();
        window.addEventListener("scroll", onScroll, {passive: true});
    }

    function init() {
        initReveal();
        initParallax();
        initCountUp();
        initStickyBookingBar();
        initHeaderScroll();
    }

    // This file loads inside Odoo's "lazy" asset bundle, which typically
    // finishes fetching well after DOMContentLoaded has already fired -
    // waiting on that event here would mean the listener never attaches.
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
