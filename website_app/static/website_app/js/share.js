/* Copy link, on post pages.
 *
 * The button ships with the `hidden` attribute set and is revealed here, so a
 * browser without the async clipboard API never shows a control that does
 * nothing. The two links beside it are plain hrefs and need no script at all.
 *
 * Shape follows theme.js: an IIFE, feature-detected, bailing early.
 */
(function () {
  "use strict";

  var button = document.querySelector("[data-copy-link]");
  if (!button) return;

  /* Both halves matter: clipboard is undefined over plain http on anything but
   * localhost, which is exactly how this site is read over the LAN. */
  if (!navigator.clipboard || !navigator.clipboard.writeText) return;

  var status = document.querySelector("[data-copy-status]");
  var restoreLabel = button.getAttribute("aria-label");
  var restoreTitle = button.getAttribute("title");
  var timer = null;

  button.hidden = false;

  function reset() {
    button.classList.remove("is-copied");
    button.setAttribute("aria-label", restoreLabel);
    button.setAttribute("title", restoreTitle);
  }

  button.addEventListener("click", function () {
    navigator.clipboard.writeText(button.dataset.url).then(
      function () {
        button.classList.add("is-copied");
        button.setAttribute("aria-label", "Link copied");
        button.setAttribute("title", "Link copied");
        /* The icon swap is the only visible feedback, and a screen reader
         * cannot see it. role="status" says it without stealing focus. */
        if (status) status.textContent = "Link copied";

        clearTimeout(timer);
        timer = setTimeout(function () {
          reset();
          if (status) status.textContent = "";
        }, 2000);
      },
      function () {
        /* Permission refused or the document is not focused. Say so rather
         * than showing a tick for a copy that never happened. */
        if (status) status.textContent = "Could not copy the link";
      }
    );
  });
})();
