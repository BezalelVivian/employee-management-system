(function () {
  "use strict";

  /* ---------- Live clock ---------- */
  function updateClock() {
    var text = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
    document.querySelectorAll("#liveClock, #heroClock").forEach(function (el) {
      el.textContent = text;
    });
  }
  updateClock();
  setInterval(updateClock, 1000);

  /* ---------- Mobile drawer ---------- */
  var body = document.body;
  var menuBtn = document.getElementById("menuBtn");
  var scrim = document.getElementById("scrim");

  function setNav(open) {
    body.classList.toggle("nav-open", open);
    if (menuBtn) {
      menuBtn.setAttribute("aria-expanded", String(open));
      menuBtn.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    }
  }

  if (menuBtn) {
    menuBtn.addEventListener("click", function () {
      setNav(!body.classList.contains("nav-open"));
    });
  }
  if (scrim) scrim.addEventListener("click", function () { setNav(false); });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") setNav(false);
  });
  document.querySelectorAll(".sidebar nav a").forEach(function (a) {
    a.addEventListener("click", function () { setNav(false); });
  });
  window
    .matchMedia("(min-width: 901px)")
    .addEventListener("change", function (e) {
      if (e.matches) setNav(false);
    });

  /* ---------- Toast ---------- */
  var toast = document.getElementById("toast");
  if (toast) {
    setTimeout(function () { toast.classList.add("hide"); }, 4500);
    setTimeout(function () { toast.remove(); }, 5000);
  }
  // Remove message parameters after the toast has been displayed.
// This prevents the same message from appearing again on refresh.
var url = new URL(window.location.href);

if (url.searchParams.has("msg")) {
  url.searchParams.delete("msg");
  url.searchParams.delete("kind");

  window.history.replaceState(
    null,
    "",
    url.pathname + url.search + url.hash
  );
}
  /* ---------- Default task date (local date, not UTC) ---------- */
  function todayLocal() {
    var d = new Date();
    var m = String(d.getMonth() + 1).padStart(2, "0");
    var day = String(d.getDate()).padStart(2, "0");
    return d.getFullYear() + "-" + m + "-" + day;
  }
  document.querySelectorAll("input[type=date]").forEach(function (el) {
    if (el.name === "task_date" && !el.value) el.value = todayLocal();
  });
})();