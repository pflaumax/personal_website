/* Theme toggle.
 *
 * <html> carries data-theme only when the visitor has chosen one; with no
 * attribute the CSS follows prefers-color-scheme, which is the default. The
 * stored value is read by an inline script in <head> so the page never paints
 * the wrong theme first. This file only handles the click.
 */
(function () {
  "use strict";

  var root = document.documentElement;
  var button = document.querySelector("[data-theme-toggle]");
  if (!button) return;

  var media = window.matchMedia("(prefers-color-scheme: dark)");

  function currentTheme() {
    return root.dataset.theme || (media.matches ? "dark" : "light");
  }

  function describe() {
    var next = currentTheme() === "dark" ? "light" : "dark";
    button.setAttribute("aria-label", "Switch to " + next + " theme");
  }

  button.addEventListener("click", function () {
    var next = currentTheme() === "dark" ? "light" : "dark";
    root.dataset.theme = next;
    try {
      localStorage.setItem("theme", next);
    } catch (e) {
      /* Private modes reject writes; the theme still applies for this page. */
    }
    describe();
  });

  /* While no explicit choice exists the page tracks the OS, so the label has
   * to track it too. addEventListener on a MediaQueryList is the modern form. */
  if (media.addEventListener) {
    media.addEventListener("change", function () {
      if (!root.dataset.theme) describe();
    });
  }

  describe();
})();
