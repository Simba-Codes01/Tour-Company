(function () {
    "use strict";

    // Traveler Reviews section on the package page: rating-bar filters, sort,
    // verified-only toggle, "show more", helpful votes, read-more clamping and
    // the write-a-review form (submitted for moderation).

    function rpc(url, params) {
        return fetch(url, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({jsonrpc: "2.0", method: "call", params: params || {}}),
        }).then(function (r) {
            if (!r.ok) { throw new Error("HTTP " + r.status); }
            return r.json();
        }).then(function (data) {
            if (data.error) { throw new Error((data.error.data && data.error.data.message) || data.error.message); }
            return data.result;
        });
    }

    function plural(n, word) {
        return n + " " + word + (n === 1 ? "" : "s");
    }

    // ---------------- Read more (clamp long reviews) ----------------
    function initClamps(root) {
        root.querySelectorAll("[data-kt-clamp]").forEach(function (p) {
            if (p.dataset.clampInit) { return; }
            p.dataset.clampInit = "1";
            p.classList.add("kt_review_clamped");
            var btn = p.parentElement.querySelector("[data-kt-readmore]");
            if (!btn) { return; }
            // Measure after layout; only offer "Read more" when text overflows.
            window.requestAnimationFrame(function () {
                if (p.scrollHeight > p.clientHeight + 2) {
                    btn.hidden = false;
                } else {
                    p.classList.remove("kt_review_clamped");
                }
            });
            btn.addEventListener("click", function () {
                var expanded = p.classList.toggle("kt_review_clamped") === false;
                btn.textContent = expanded ? "Show less" : "Read more";
                btn.setAttribute("aria-expanded", expanded ? "true" : "false");
            });
        });
    }

    // ---------------- Helpful votes ----------------
    function initHelpful(root) {
        root.querySelectorAll(".kt_review_helpful").forEach(function (btn) {
            if (btn.dataset.helpfulInit) { return; }
            btn.dataset.helpfulInit = "1";
            btn.addEventListener("click", function () {
                if (btn.disabled) { return; }
                btn.disabled = true;
                rpc(btn.getAttribute("data-helpful-url")).then(function (res) {
                    btn.classList.toggle("kt_review_helpful_active", !!res.voted);
                    btn.setAttribute("aria-pressed", res.voted ? "true" : "false");
                    btn.querySelector(".kt_review_helpful_count").textContent = res.count || "";
                    if (res.voted) {
                        btn.classList.remove("kt_review_helpful_pop");
                        void btn.offsetWidth; // restart the animation
                        btn.classList.add("kt_review_helpful_pop");
                    }
                }).catch(function () { /* leave the button as it was */ }).finally(function () {
                    btn.disabled = false;
                });
            });
        });
    }

    function initCards(root) {
        initClamps(root);
        initHelpful(root);
    }

    // ---------------- Filter / sort / show more ----------------
    function initListing(section) {
        var url = section.getAttribute("data-reviews-url");
        var list = section.querySelector("[data-kt-review-list]");
        var moreBtn = section.querySelector("[data-kt-review-more]");
        var bars = section.querySelectorAll(".kt_review_bar");
        var sortSelect = section.querySelector("[data-kt-review-sort]");
        var verifiedToggle = section.querySelector("[data-kt-review-verified]");
        var clearChip = section.querySelector("[data-kt-review-clear]");
        var showing = section.querySelector(".kt_reviews_showing");
        var emptyFiltered = section.querySelector(".kt_review_empty_filtered");

        var state = {
            star: 0,
            verified: false,
            sort: "newest",
            offset: parseInt(section.getAttribute("data-next-offset"), 10) || 0,
            total: parseInt(section.getAttribute("data-total"), 10) || 0,
        };
        var requestSeq = 0;

        function updateChrome() {
            bars.forEach(function (bar) {
                var active = parseInt(bar.getAttribute("data-star"), 10) === state.star;
                bar.classList.toggle("kt_review_bar_active", active);
                bar.setAttribute("aria-pressed", active ? "true" : "false");
            });
            section.classList.toggle("kt_reviews_filtered", !!state.star);
            if (clearChip) {
                var parts = [];
                if (state.star) { parts.push(state.star + "-star"); }
                if (state.verified) { parts.push("verified"); }
                clearChip.hidden = !parts.length;
                clearChip.querySelector(".kt_review_chip_text").textContent = parts.join(", ");
            }
            if (showing) {
                showing.textContent = plural(state.total, "review");
            }
            if (moreBtn) { moreBtn.hidden = state.offset >= state.total; }
            if (emptyFiltered) { emptyFiltered.hidden = state.total > 0; }
        }

        function load(append) {
            var seq = ++requestSeq;
            list.setAttribute("aria-busy", "true");
            section.classList.add("kt_reviews_loading");
            if (moreBtn && append) { moreBtn.disabled = true; }
            return rpc(url, {
                star: state.star || null,
                verified: state.verified,
                sort: state.sort,
                offset: append ? state.offset : 0,
            }).then(function (res) {
                if (seq !== requestSeq) { return; } // a newer request superseded this one
                var tmp = document.createElement("div");
                tmp.innerHTML = res.html;
                var cards = Array.prototype.slice.call(tmp.children);
                if (!append) { list.innerHTML = ""; }
                cards.forEach(function (card) {
                    card.classList.add("kt_review_card_enter");
                    list.appendChild(card);
                });
                state.total = res.total;
                state.offset = res.next_offset;
                initCards(list);
                // Trigger the enter transition on the next frame.
                window.requestAnimationFrame(function () {
                    cards.forEach(function (card) { card.classList.remove("kt_review_card_enter"); });
                });
                if (append && cards[0]) {
                    var focusTarget = cards[0].querySelector(".kt_review_helpful");
                    if (focusTarget) { focusTarget.focus({preventScroll: true}); }
                }
                updateChrome();
            }).catch(function () {
                if (seq === requestSeq && showing) {
                    showing.textContent = "Couldn't load reviews. Please try again.";
                }
            }).finally(function () {
                if (seq !== requestSeq) { return; }
                list.setAttribute("aria-busy", "false");
                section.classList.remove("kt_reviews_loading");
                if (moreBtn) { moreBtn.disabled = false; }
            });
        }

        bars.forEach(function (bar) {
            bar.addEventListener("click", function () {
                var star = parseInt(bar.getAttribute("data-star"), 10);
                state.star = state.star === star ? 0 : star;
                load(false);
                var toolbar = section.querySelector(".kt_reviews_toolbar");
                if (toolbar && toolbar.getBoundingClientRect().top < 0) {
                    toolbar.scrollIntoView({behavior: "smooth", block: "start"});
                }
            });
        });
        if (sortSelect) {
            sortSelect.addEventListener("change", function () {
                state.sort = sortSelect.value;
                load(false);
            });
        }
        if (verifiedToggle) {
            verifiedToggle.addEventListener("change", function () {
                state.verified = verifiedToggle.checked;
                load(false);
            });
        }
        if (clearChip) {
            clearChip.addEventListener("click", function () {
                state.star = 0;
                state.verified = false;
                if (verifiedToggle) { verifiedToggle.checked = false; }
                load(false);
            });
        }
        if (moreBtn) {
            moreBtn.addEventListener("click", function () { load(true); });
        }
    }

    // ---------------- Star picker ----------------
    function initStarPicker(form) {
        var picker = form.querySelector(".kt_star_picker");
        if (!picker) { return; }
        var labels = picker.querySelectorAll(".kt_star_label");
        var inputs = picker.querySelectorAll(".kt_star_input");
        var text = picker.querySelector(".kt_star_picker_text");
        var defaultText = text.textContent;

        function selected() {
            var checked = picker.querySelector(".kt_star_input:checked");
            return checked ? parseInt(checked.value, 10) : 0;
        }

        function paint(value) {
            labels.forEach(function (label) {
                label.classList.toggle("kt_star_lit", parseInt(label.getAttribute("data-value"), 10) <= value);
            });
            var current = value && picker.querySelector('.kt_star_label[data-value="' + value + '"]');
            text.textContent = current ? current.getAttribute("data-text") : defaultText;
            text.classList.toggle("kt_star_picker_text_set", !!value);
        }

        labels.forEach(function (label) {
            label.addEventListener("mouseenter", function () {
                paint(parseInt(label.getAttribute("data-value"), 10));
            });
        });
        picker.querySelector(".kt_star_picker_stars").addEventListener("mouseleave", function () {
            paint(selected());
        });
        inputs.forEach(function (input) {
            input.addEventListener("change", function () {
                paint(selected());
                var label = picker.querySelector('label[for="' + input.id + '"]');
                if (label) {
                    label.classList.remove("kt_star_bounce");
                    void label.offsetWidth;
                    label.classList.add("kt_star_bounce");
                }
                clearFieldError(form, "rating");
            });
        });
        form.addEventListener("reset", function () {
            window.setTimeout(function () { paint(0); }, 0);
        });
    }

    // ---------------- Write-a-review form ----------------
    function setFieldError(form, field, message) {
        var box = form.querySelector('[data-kt-error="' + field + '"]');
        var wrap = form.querySelector('[data-kt-field="' + field + '"]');
        if (box) { box.textContent = message || ""; }
        if (wrap) { wrap.classList.toggle("kt_review_field_invalid", !!message); }
        var input = form.querySelector('[name="' + field + '"]');
        if (input) { input.setAttribute("aria-invalid", message ? "true" : "false"); }
    }

    function clearFieldError(form, field) {
        setFieldError(form, field, "");
    }

    function validate(form) {
        var errors = {};
        var data = new FormData(form);
        if (!data.get("rating")) { errors.rating = "Please choose a star rating."; }
        if (!(data.get("name") || "").trim()) { errors.name = "Please enter your name."; }
        var email = (data.get("email") || "").trim();
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { errors.email = "Please enter a valid email address."; }
        if ((data.get("comment") || "").trim().length < 20) {
            errors.comment = "Please write at least 20 characters about your trip.";
        }
        return errors;
    }

    function initForm(section) {
        var panel = section.querySelector(".kt_review_form_panel");
        if (!panel) { return; }
        var form = panel.querySelector(".kt_review_form");
        var thanks = panel.querySelector(".kt_review_thanks");
        var status = form.querySelector(".kt_review_form_status");
        var submitBtn = form.querySelector(".kt_review_submit");
        var textarea = form.querySelector("textarea[name=comment]");
        var counter = form.querySelector(".kt_review_counter");
        var openers = section.querySelectorAll("[data-kt-review-open]");
        var lastOpener = null;

        function setOpen(open) {
            panel.hidden = !open;
            openers.forEach(function (btn) { btn.setAttribute("aria-expanded", open ? "true" : "false"); });
            if (open) {
                panel.classList.remove("kt_review_form_panel_enter");
                void panel.offsetWidth;
                panel.classList.add("kt_review_form_panel_enter");
                panel.scrollIntoView({behavior: "smooth", block: "start"});
                var first = form.querySelector(".kt_star_input");
                if (first && !form.hidden) { first.focus({preventScroll: true}); }
            } else if (lastOpener) {
                lastOpener.focus({preventScroll: true});
            }
        }

        openers.forEach(function (btn) {
            btn.addEventListener("click", function () {
                lastOpener = btn;
                setOpen(panel.hidden);
            });
        });
        panel.querySelectorAll("[data-kt-review-close]").forEach(function (btn) {
            btn.addEventListener("click", function () { setOpen(false); });
        });
        panel.addEventListener("keydown", function (ev) {
            if (ev.key === "Escape") { setOpen(false); }
        });

        function updateCounter() {
            var len = textarea.value.length;
            counter.textContent = len + " / 3000";
            counter.classList.toggle("kt_review_counter_low", len > 0 && len < 20);
        }
        textarea.addEventListener("input", function () {
            updateCounter();
            if (textarea.value.trim().length >= 20) { clearFieldError(form, "comment"); }
        });
        ["name", "email"].forEach(function (field) {
            var input = form.querySelector('[name="' + field + '"]');
            input.addEventListener("input", function () { clearFieldError(form, field); });
        });

        function setBusy(busy) {
            submitBtn.disabled = busy;
            submitBtn.querySelector(".kt_review_submit_label").hidden = busy;
            submitBtn.querySelector(".kt_review_submit_busy").hidden = !busy;
        }

        function showErrors(errors, message) {
            ["rating", "name", "email", "comment"].forEach(function (field) {
                setFieldError(form, field, errors[field]);
            });
            status.hidden = !message;
            status.textContent = message || "";
            var firstInvalid = form.querySelector('[aria-invalid="true"]');
            if (firstInvalid) { firstInvalid.focus(); }
        }

        form.addEventListener("submit", function (ev) {
            ev.preventDefault();
            var errors = validate(form);
            if (Object.keys(errors).length) {
                showErrors(errors, "Please fix the highlighted fields.");
                return;
            }
            showErrors({}, "");
            var data = new FormData(form);
            setBusy(true);
            rpc(form.getAttribute("action"), {
                rating: parseInt(data.get("rating"), 10),
                name: data.get("name"),
                email: data.get("email"),
                title: data.get("title"),
                comment: data.get("comment"),
                travel_type: data.get("travel_type") || null,
                website: data.get("website"),
            }).then(function (res) {
                if (res && res.success) {
                    form.hidden = true;
                    thanks.hidden = false;
                    thanks.querySelector(".kt_review_thanks_msg").textContent =
                        res.message || "Thanks! Your review will appear once our team has checked it.";
                    thanks.focus();
                    form.reset();
                    updateCounter();
                    openers.forEach(function (btn) { btn.hidden = true; });
                } else {
                    showErrors((res && res.fields) || {}, (res && res.error) || "Something went wrong. Please try again.");
                }
            }).catch(function () {
                showErrors({}, "We couldn't send your review. Check your connection and try again.");
            }).finally(function () {
                setBusy(false);
            });
        });

        initStarPicker(form);
        updateCounter();
    }

    function init() {
        var section = document.getElementById("kt_reviews");
        if (!section || section.dataset.reviewsInit) { return; }
        section.dataset.reviewsInit = "1";
        initCards(section);
        initListing(section);
        initForm(section);
        if (window.location.hash === "#kt_reviews_write") {
            var opener = section.querySelector("[data-kt-review-open]");
            if (opener) { opener.click(); }
        }
    }

    // Loaded in Odoo's lazy frontend bundle, which can finish after
    // DOMContentLoaded has already fired.
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
