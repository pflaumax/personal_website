/* Back to top, on post pages.
 *
 * Two elements, not one: the docked link in the post footer is the real
 * control and works with this file absent (href="#top" is the top of the
 * document by definition), while the floating twin is a mouse convenience that
 * only exists once you are far enough down for the docked one to be off
 * screen. Moving a single element between fixed and static instead would need
 * a placeholder to hold its slot in the footer row, and would leave the page
 * jumping at the moment it swapped.
 *
 * Shape follows theme.js: an IIFE, feature-detected, bailing early.
 */
(function () {
  "use strict";

  var floater = document.querySelector("[data-back-to-top-float]");
  var docked = document.querySelector("[data-back-to-top]:not([data-back-to-top-float])");
  var sentinel = document.querySelector("[data-scroll-sentinel]");

  /* --- smooth scroll, on both copies ------------------------------------ */
  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)");

  Array.prototype.forEach.call(
    document.querySelectorAll("[data-back-to-top]"),
    function (link) {
      link.addEventListener("click", function (event) {
        if (!window.scrollTo) return; /* let the plain fragment jump happen */
        event.preventDefault();
        window.scrollTo({
          top: 0,
          behavior: reduced.matches ? "auto" : "smooth",
        });
        /* Scrolling alone leaves the keyboard where it was, so the next Tab
         * would resume at the bottom of the page. preventScroll keeps the
         * focus call from fighting the smooth scroll it just started. */
        var top = document.querySelector(".logotype a");
        if (top && top.focus) top.focus({ preventScroll: true });
      });
    }
  );

  /* --- is there anything to come back from? ------------------------------ */
  /* A post of one sentence still rendered "Back to top" under it, pointing at
   * a top that never left the screen. Page height is a runtime fact — images
   * and the reader's window decide it, not the stored content — so it is
   * measured here rather than guessed from the body length in the view. The
   * link is rendered server-side and removed here, never the other way round:
   * with JavaScript off a long post keeps a working control, and the worst a
   * short one gets is a link that scrolls nowhere. */
  function worthScrolling() {
    var overflow =
      document.documentElement.scrollHeight - window.innerHeight;
    return overflow > window.innerHeight * 0.6;
  }

  /* --- when the floating twin is visible --------------------------------- */
  if (!floater || !docked || !sentinel || !window.IntersectionObserver) return;

  var pastTop = false;
  var dockVisible = false;
  var enough = false;

  function update() {
    floater.classList.toggle("is-visible", enough && pastTop && !dockVisible);
  }

  function measure() {
    enough = worthScrolling();
    docked.hidden = !enough;
    update();
  }

  measure();
  /* Late images change the answer, and so does turning a phone sideways. */
  window.addEventListener("load", measure);
  window.addEventListener("resize", measure);

  /* Past the post header means past the point where a way back up is worth
   * offering; the docked link taking over at the bottom is what stops the two
   * from ever showing at once. */
  new IntersectionObserver(function (entries) {
    pastTop = !entries[0].isIntersecting;
    update();
  }).observe(sentinel);

  new IntersectionObserver(function (entries) {
    dockVisible = entries[0].isIntersecting;
    update();
  }).observe(docked);
})();
