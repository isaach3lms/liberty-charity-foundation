/* Liberty Charity Foundation: nav toggle and scroll reveal. Nothing else. */
(function () {
  "use strict";

  var toggle = document.querySelector("[data-nav-toggle]");
  var nav = document.getElementById("nav");
  var scrim = document.querySelector("[data-nav-scrim]");
  var navClose = document.querySelector("[data-nav-close]");

  if (toggle && nav) {
    var openNav = function () {
      nav.classList.add("is-open");
      if (scrim) { scrim.classList.add("is-open"); }
      document.body.classList.add("nav-open");
      toggle.setAttribute("aria-expanded", "true");
    };
    var closeNav = function () {
      nav.classList.remove("is-open");
      if (scrim) { scrim.classList.remove("is-open"); }
      document.body.classList.remove("nav-open");
      toggle.setAttribute("aria-expanded", "false");
    };

    toggle.addEventListener("click", function () {
      if (nav.classList.contains("is-open")) { closeNav(); } else { openNav(); }
    });
    if (navClose) { navClose.addEventListener("click", closeNav); }
    if (scrim) { scrim.addEventListener("click", closeNav); }

    // Close on Escape and when a drawer link is tapped.
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && nav.classList.contains("is-open")) { closeNav(); }
    });
    nav.querySelectorAll("a").forEach(function (a) {
      a.addEventListener("click", closeNav);
    });

    // If the viewport grows past the desktop breakpoint, reset drawer state.
    window.matchMedia("(min-width: 860px)").addEventListener("change", function (ev) {
      if (ev.matches) { closeNav(); }
    });
  }

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var items = document.querySelectorAll(".reveal");

  if (reduced || !("IntersectionObserver" in window)) {
    items.forEach(function (el) { el.classList.add("is-in"); });
    return;
  }

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-in");
        io.unobserve(entry.target);
      }
    });
  }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });

  items.forEach(function (el, i) {
    el.style.transitionDelay = Math.min(i % 4, 3) * 70 + "ms";
    io.observe(el);
  });

  /* Contact form: submit to Web3Forms over fetch, then route to the branded
     thank-you page. Without fetch, the form posts natively to Web3Forms and
     that service shows its own success page. */
  var cform = document.getElementById("contact-form");
  if (cform && window.fetch) {
    var status = document.getElementById("form-status");
    var btn = cform.querySelector("button[type=submit]");

    cform.addEventListener("submit", function (e) {
      if (!cform.checkValidity()) { return; }  // let the browser show field errors
      e.preventDefault();

      var label = btn ? btn.textContent : "";
      if (btn) { btn.disabled = true; btn.textContent = "Sending..."; }
      if (status) { status.hidden = true; status.className = "form-status"; }

      fetch(cform.action, {
        method: "POST",
        body: new FormData(cform),
        headers: { "Accept": "application/json" }
      })
        .then(function (r) {
          return r.json().then(function (data) { return { ok: r.ok, data: data }; });
        })
        .then(function (res) {
          if (res.ok && res.data && res.data.success) {
            window.location.href = "/contact/thank-you";
          } else {
            fail(res.data && res.data.message ? res.data.message
              : "The message did not send. Please try again.");
          }
        })
        .catch(function () {
          fail("The message did not send. Please check your connection and try again.");
        });

      function fail(msg) {
        if (btn) { btn.disabled = false; btn.textContent = label; }
        if (status) {
          status.textContent = msg;
          status.className = "form-status is-error";
          status.hidden = false;
        }
      }
    });
  }
})();
