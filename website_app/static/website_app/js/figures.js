/* Toggles and dials for figure partials (website_app/templates/website_app/figures/).
 *
 * A toggle names the element it acts on and the class it flips:
 *   data-fig-toggle="<id>" data-fig-class="<class>"
 * aria-pressed carries the state for anyone not looking at it.
 *
 * The melt dials write straight onto the filter primitives. There is no
 * animation loop: one attribute write, one repaint.
 *
 * Shape follows theme.js: an IIFE, feature-detected, bailing early. Every
 * figure renders at its defaults with this file absent.
 */
(function () {
  "use strict";

  document.querySelectorAll("[data-fig-toggle]").forEach(function (button) {
    var target = document.getElementById(button.dataset.figToggle);
    if (!target) return;
    button.addEventListener("click", function () {
      var on = target.classList.toggle(button.dataset.figClass);
      button.setAttribute("aria-pressed", on ? "true" : "false");
    });
  });

  var noise = document.getElementById("fig-melt-noise");
  var map = document.getElementById("fig-melt-map");
  var freq = document.getElementById("fig-melt-freq");
  var scale = document.getElementById("fig-melt-scale");
  var freqOut = document.getElementById("fig-melt-freq-out");
  var scaleOut = document.getElementById("fig-melt-scale-out");
  if (!noise || !map || !freq || !scale) return;

  function apply() {
    var f = freq.value / 100;
    noise.setAttribute("baseFrequency", f);
    map.setAttribute("scale", scale.value);
    freqOut.textContent = f.toFixed(2);
    scaleOut.textContent = scale.value;
  }
  freq.addEventListener("input", apply);
  scale.addEventListener("input", apply);
  apply();
})();
