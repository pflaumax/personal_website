/* The glitch, home page only.
 *
 * A rebuild of the effect from fbergman.se (source: github.com/henrik/fbergmanse,
 * where it is called "glitch"). The whole thing is one class toggling one static
 * SVG filter — there is no animation, so there is nothing to cancel mid-flight
 * and no frame budget to keep. The filter itself lives in base.html.
 *
 * No state is stored anywhere, deliberately: navigating away clears it, so the
 * page can never be left permanently melted. Escape and a second click are the
 * other two ways out.
 *
 * Shape follows theme.js: an IIFE, feature-detected, bailing early.
 */
(function () {
  "use strict";

  var trigger = document.querySelector("[data-melt-trigger]");
  var target = document.querySelector("[data-melt-target]");
  if (!trigger || !target) return;

  var activeClass = "is-melted";

  function setState(on) {
    target.classList.toggle(activeClass, on);
    trigger.setAttribute("aria-pressed", on ? "true" : "false");
  }

  trigger.addEventListener("click", function () {
    setState(!target.classList.contains(activeClass));
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") setState(false);
  });
})();
