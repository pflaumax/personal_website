# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All commands assume the venv is active: `source .venv/bin/activate` (Python 3.14 locally; README targets 3.12+).

```bash
python manage.py runserver              # dev server
python manage.py migrate
python manage.py makemigrations <app>
python manage.py collectstatic          # required before prod; WhiteNoise uses a manifest
python manage.py shell_plus             # django-extensions (SHELL_PLUS=ipython, not installed by default)

python manage.py test                   # whole suite
python manage.py test website_app       # one app
python manage.py test stats.tests.SomeTestCase.test_method   # one test

python scripts/create_superuser.py      # idempotent, reads DJANGO_SUPERUSER_* from .env

ruff check .                            # lint  (E, F, I, UP)
ruff check --fix .
ruff format .                           # format (double quotes, line-length 88)
ruff format --check .
```

**Ruff is configured and the tree passes it — run it before committing Python.** The config is
`[tool.ruff]` in `pyproject.toml` (`ruff==0.16.3`, dev-only, in `requirements-dev.txt`), which is
easy to miss because it is the only thing in that file and there is no CI enforcing it. Migrations
and `*.md` are excluded; `scripts/create_superuser.py` is exempt from `E402` because
`django.setup()` has to run before its imports, and `website_project/settings.py` from `E501` for
Django's own `AUTH_PASSWORD_VALIDATORS` dotted paths. Note that `ruff format` will not split a long
string literal, so an `E501` inside one is always a manual wrap.

There is no type-check config (no mypy.ini) and no test framework beyond Django's runner. Tests use `django.test.TestCase` and live in `website_app/tests.py`, `stats/tests.py`, and `tools/tests.py`. Coverage is concentrated on `Post.save()` slug generation, `PageViewMiddleware` exclusion rules, `/api/stats/` authorization, the RSS feed, and per-page metadata — the areas most likely to break silently.

**In dev, `collectstatic` is not optional and neither is restarting the server.** WhiteNoise's manifest storage is used with `DEBUG=True` too, so a new or edited static file 500s (`Missing staticfiles manifest entry`) until `collectstatic` runs — and `runserver` caches the manifest in memory at startup, so it keeps serving the old hashed name until restarted. Editing CSS therefore means: edit → `collectstatic` → restart.

**Every `manage.py` command needs a populated `.env`.** `website_project/settings.py` raises `ValueError` at import if `DJANGO_ADMIN_URL` or `SECRET_KEY` is missing, so a missing `.env` breaks even `--help`.

## Architecture

Django 5.2 project, `website_project/` is the config package; three first-party apps.

**`website_app`** — blog, static pages, media, error handlers. Owns `base.html` (site nav, footer, `<head>`) which every other template in the project extends, and the whole static bundle (`static/website_app/`: `css/style.css`, `js/theme.js`, `js/back-to-top.js`, `js/share.js`, `js/tools.js`, the font, the sprite). `Post.save()` auto-generates a unique slug from the title, re-slugging only when the title actually changes (`title_has_changed()` re-fetches the row to compare); collisions get a `-1`, `-2` suffix. Views are plain function views; the four `error_4xx/500` views are wired as `handler400/403/404/500` in `website_project/urls.py`.

The six public projects live in **`website_app/projects_data.py`**, not in the template: `/projects/` renders the whole `PROJECTS` tuple and the home page slices `[:3]`. Reordering the tuple reorders both pages. An entry with `demo_url`/`demo_label` also renders a demo link — that is how `/tools/` is reached.

**RSS** is `website_app/feeds.py` (`django.contrib.syndication`, no new dependency) at `/feed/`. Two things there are deliberate and easy to undo by accident: it is served as `application/xml`, not `application/rss+xml`, because browsers have no renderer for the latter and clicking the link downloads a file — the overriding attribute is `content_type`, *not* `mime_type` (the pre-1.7 name, still present on `Enclosure`, so overriding it fails silently). And `item_pubdate` must convert `Post.date_added`, which is a `DateField`, into an aware datetime. Item summaries come from `Post.excerpt()`, which unescapes entities — `strip_tags` leaves them, and the framework escapes them again, so `&nbsp;` otherwise reaches readers as `&amp;nbsp;`.

**Post pages carry their own furniture**, all of it in `post.html`: a `.post-back` link to
`/blog/` *above* the title, a share row, and **two** back-to-top controls.

The share row is **three icons and no visible label** — Bluesky, mail, copy link. The `<ul>`
carries `aria-label="Share this post"` and each control its own `aria-label` plus a `title`: with
no words on screen those names are all that stands between a screen reader and three empty links. The
targets are chosen, not arbitrary: nothing advertising-funded (a test asserts X, Telegram, Reddit
and Facebook never appear), and copy link is what covers Signal, Matrix and every other chat
without embedding any of them. **Mastodon is deliberately absent** — its `/share` path only works
on the reader's own instance, so it needs either a third-party redirector or an instance prompt —
a dependency on someone else's domain, or a whole UI for one button. The two link URLs are built in
`views._share_links`, not the template, so the encoding stays testable. The copy button ships with
`hidden` set and `share.js` reveals it only where `navigator.clipboard.writeText` exists — a
control that silently does nothing is worse than an absent one, and `clipboard` is undefined over
plain http, which is how the site is read over the LAN. Its only visible feedback is an icon swap,
so a `role="status"` span announces it too. The tick takes `--accent` — green means state, same
token as focus and hover — and the rule is written **twice**, plain and `:hover`. That is not
redundant: the pointer is by definition still on the button at the instant it becomes a tick, so
`.share-link:hover` at (0,2,0) would outrank a bare `.is-copied` at (0,1,0) and repaint the tick
back to `--text`. The Bluesky butterfly is the one **filled** mark among
stroke icons: it is set a size down (17px against 19px) *and* to `opacity: .85`, because fill
carries more ink than stroke at the same box.

`.share-list`'s gap is **exactly twice** `.share-link`'s padding, so the 32px hit areas meet edge
to edge — less and adjacent targets overlap, more and they leave dead gaps.

Two alignment rules keep the footer row level, and both are easy to undo by accident.
`.post-footer-row` is `align-items: center`, **not** `baseline`: a `<ul>` of icons has no text, so
its baseline is synthesised from its bottom edge and the cluster floats above the "Back to top"
label. And the docked `.back-to-top` takes `line-height: 1` so its box hugs its ink — a 1.5 line
box is taller than the text and bottom-heavy inside it, which left the label riding low against
the icons opposite. The floating twin restores `var(--line-height)`, because its box is padding,
not type.

**`.blog-post` carries no measure.** The 68ch cap lives on `.post-content`, the only part being
read. It used to sit on the article, which capped the `.post-footer` rule too — leaving three
horizontal rules on one page at two different widths. The docked one in `.post-footer` is the real control and needs no JavaScript —
`href="#top"` with no element of that id is defined to mean the top of the document. The floating
twin is `aria-hidden` and `tabindex="-1"` on purpose: it is a mouse convenience, and putting it in
the tab order would only add a second identical stop. `back-to-top.js` shows it (two
`IntersectionObserver`s: past the post header, and the docked link not in view) and upgrades the
jump to a smooth scroll. It also **removes both controls when the page barely scrolls**
(`scrollHeight - innerHeight > innerHeight * 0.6`, re-measured on `load` and `resize`): page height
is a runtime fact that images and the window decide, so it cannot be guessed from body length in
the view. The direction matters — the markup renders server-side and JS only *removes* it, so a
long post keeps a working control with JavaScript off.

The float is positioned against the **container's** right edge, not the viewport's
(`right: max(1.25rem, calc(50vw - var(--container-width) / 2 + var(--spacing-unit)))`), so it sits
directly above where the docked link appears and the hand-off at the end of the post reads as one
object settling into place. It is kept small and **opaque**: the honest way to stop a floating
label covering prose is to make it small, not see-through — and a frosted-glass blur is the one
effect a pixel-language site cannot borrow. Page-specific scripts go in `{% block extra_scripts %}`, after
`theme.js`.

`_share_links` passes `quote_via=quote` to `urlencode`. The default is `quote_plus`, and a `+` for
a space survives verbatim into a mail client's body — `%20` is the only encoding that works for
both a query string and a `mailto:`.

**Page titles and meta** travel in the **view context** (`page_title`, `page_description`, optional `page_type` / `page_noindex`), not in template blocks: a Django block can only be emitted once and the same string is needed in `<title>`, `og:title` and `twitter:title`. `base.html` derives `doc_title` / `doc_description` / `canonical_url` once with `{% firstof … as … %}`. Any new view that renders a page must pass these or it inherits the site defaults. The canonical URL is built from `request.path`, so query strings are excluded.

**`tools`** — a single template-rendering view. **Not in the primary nav** (Home · Blog · Projects · Contact); it is linked from the *My Personal Website* entry on `/projects/` as a demo, because it is a demo, not a product. Its Todo List and Pomodoro Timer are entirely client-side (`static/website_app/js/tools.js`, browser session storage). The app has **no `models.py`**; migrations `0001`–`0003` create and then delete a `Task` model — that history is intentional, do not "fix" it by adding models back.

**`stats`** — `PageViewMiddleware` increments a per-path `PageView` counter, atomically via `F("count") + 1`. It records **after** the response, and only for `GET` requests that returned 2xx — redirects, 404s and errors are not counted, so bot scans no longer create rows. Exclusions in `stats/middleware.py`: exact paths (incl. `/media-list/` and `/feed/` — a feed reader polls forever), asset suffixes, over-length paths, and the prefixes `/static/ /media/ /admin/ /api/ /tinymce/` plus `settings.ADMIN_URL` (the `/admin/` entry is only the decoy route). Any new non-page endpoint must be added there.

`/api/stats/` is **staff-only** — it returns 404 for everyone else via `staff_member_required_or_404` (`website_project/decorators.py`), which raises `Http404` instead of redirecting, because Django's own `staff_member_required` leaks `ADMIN_URL` in the `Location` header. `?limit=` is clamped to `[0, 100]`; `0` means summary-only. Purge admin rows recorded before these fixes with `python manage.py purge_admin_pageviews [--prefix <old-url>] [--dry-run]`.

### Front end: tokens, themes, type

One stylesheet (`css/style.css`), no build step, no npm. Everything below is a trap that has
already been hit once.

**Themes have three states, not two.** `:root` carries the *complete* light palette;
`@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { … } }` and
`:root[data-theme="dark"] { … }` each redefine the same token list. No attribute on `<html>`
means "follow the OS", which is the common case. **Never declare a colour only inside a dark
block** — it will not apply in the un-stamped state. The stored preference is read by an inline
script in `<head>` *before first paint* (`js/theme.js` only handles the click); every
`localStorage` access is wrapped in `try/catch` because it throws outright in some privacy modes.

**`--mark` and `--fill` are not interchangeable.** `--mark` is the highlighter band under a link;
`--fill` is a filled surface (chips, primary buttons). On paper one colour does both jobs, so
they are equal in light. On a dark ground they pull apart: the band must clear the background by
roughly 3:1 to stay visible, while a filled block at that strength reads as a sticker. Related:
**every filled control needs the `--fill-line` hairline.** Without it the quiet dark fill sits too
close to the neutral surfaces and "primary" stops reading as primary.

**Font weights are per-theme, and the dark set steps *down*.** Light strokes on a dark ground
irradiate — 300 there matches about 350 on paper. `--weight-body` is 280 light / 255 dark. The
variable Monaspace subset (`fonts/monaspace/`, 59 KB, `wght 200..800` + `slnt`) is what makes
this possible; its provenance and exact rebuild command are in the README beside it. Two
`@font-face` rules share one URL — the second is `font-style: oblique 0deg 11deg`, which maps
onto the `slnt` axis for real italics. `font-synthesis: none` is set deliberately, so a missing
weight shows rather than being faked.

**The 8-bit corner is on pseudo-elements, never on the element.** `clip-path` clips everything an
element paints *including its focus ring*, so putting it on a `<button>` silently removes
keyboard focus. `::before` is the outline, `::after` the fill inset by `--px-weight`, both at
`z-index: -1`. Two consequences: `--px-fill: transparent` is a bug, not an outline (the fill layer
covers the outline layer, so the line colour floods the shape — use `var(--bg)`, which also means
outlined pixel elements only work on the page ground); and `<input>` cannot have pseudo-elements,
so form fields keep square corners. The notch only reads on a slim shape — on a chunky filled
block it becomes ornament, which is why chip padding is deliberately tiny.

**Pixel geometry needs a shape big enough to carry it.** A stepped underline was tried twice at
text size and rejected both times: it reads as a dotted line hovering over a rule, not as one
stepped edge. The pixel language now lives in *motion* (`steps()` on the wordmark jump, the button
press, the link band's colour change) and in the one place with room for it — the 143px sprite.
That sprite is a CSS `mask-image`, not an `<img>`: the source is near-white on transparency, so
as an image it would vanish on paper; masked, it takes `var(--text)` and works in both themes
from one asset, at 1:1 because it has genuine single-pixel detail.

**Green means interaction and state.** Links take `--text` and the band carries the affordance;
`--accent` is for hover, focus rings and the live dot. Colouring link text *and* underlining it
signals twice, and the doubling is what tints the whole page green.

Every page hangs off one left edge at `--container-width: 720px`; prose is capped at 48–68ch.
`prefers-reduced-motion` is respected in four places — the wordmark jump, the link band, the
button press, and the floating back-to-top's fade — check it when adding a fifth.

The hover band is scoped as `.post-footer-row .back-to-top:hover`. Unscoped it also applied to the
floating chip, where the global 5px link band was clipped by the corner notches into two stray
green fragments at the bottom corners — a bug that looked like a feature. The chip's own hover
moves `--px-line` to `--accent` instead, which is the same statement made deliberately.

`.back-to-top-float` is the **only fixed-position element on the site**, and the only pixel
element that takes the `::before`/`::after` layers without joining the shared base rule in §10b —
that rule sets `position: relative`. Its own rule in §6 repeats what it needs, including an
explicit `z-index` above 0 so the `z-index: -1` pseudo-layers stay behind its label but in front
of the page scrolling underneath.

**The glitch is home-page only, and the scope is load-bearing.** Clicking the wordmark toggles
`.is-melted` on `.container`, which applies a static SVG filter (`feTurbulence` → `feDisplacementMap`,
`js/melt.js`, filter defined in `base.html`). Rebuilt from `github.com/henrik/fbergmanse`, where
the original calls it *glitch*, not melt. Three constraints:

- **The target is `.container` — header, main and footer together.** Half a melted page reads as a
  rendering bug rather than a joke, and the original melts its own trigger too. Nothing gets
  trapped: a CSS filter is paint-only, so hit testing still uses the real geometry and every
  control stays clickable within a few pixels of where it appears.
- **Keep it off every other page.** A filtered ancestor turns `position: fixed` into absolute, so
  running this on a post page would drag `.back-to-top-float` along with the melting text instead
  of leaving it pinned. `index()` passes `is_home`, which is the only switch.
- **On home the wordmark is a `<button>`, not a link** (`.logotype-mark`), because on that page the
  link pointed at the page you were already on. A link that conditionally refuses to navigate would
  break middle-click and lie to assistive tech; a button is the honest element for "this does
  something". Everywhere else the wordmark is an ordinary link home.
- **There is no `prefers-reduced-motion` rule and that is deliberate** — the filter is static,
  nothing animates. Do not add a `transition` on `filter`: that *would* be motion, and it would
  interpolate the filter every frame.

The SVG holder takes `visibility: hidden`, not `display: none`, which can stop the filter reference
resolving. No state is stored, so navigating away always clears the effect.

**The paper is aged, and both grounds carry grain.** The light palette is no longer an off-white:
`--bg` is `#fbf5e5` and renders at about `#e8e3d4` once the grain multiplies into it — warmth
(r−b) of 20 against the old 5. Every neutral was warmed to match, because a cool grey on a cream
ground reads as dirt rather than as a line, and the green ramp moved a few degrees toward the
paper's yellow because mint over cream goes acid. **The accent is now tied to the paper: change
one and retune the other.**

The grain is a data-URI noise field in `body`'s *background*, blended with `background-blend-mode`
— not a fixed overlay using `mix-blend-mode`. An overlay has to be blended against the whole
composited page on every scrolled frame; blending inside one element's own background happens
once. The tile is a fixed `200x200` with `stitchTiles="stitch"`: without a size the browser
generates Perlin noise across the entire viewport and regenerates it on resize.

**The dial that works is the base colour, not the noise strength**, and this took three attempts to
learn. A blend mode only pushes one way — `multiply` darkens, `screen` lifts — so turning the noise
up drags the ground with it. On dark, strength alone put `#21201a` at `#3c3b36`, which met `--rule`
and made every hairline on the site vanish. Give the noise headroom instead: dark `--bg` is
`#0d0c08` and renders at `#23221e`, two levels off the palette's `#21201a`, so the rules never had
to move. Light works the same way in the other direction, with `--bg` lighter than the ground you
see.

`overlay` and `soft-light` are dead ends for this. They compress toward the base, so on a dark
ground they behave like `multiply` and on a light one like `screen` — measured σ of 1–2 either way,
which is no texture at all.

**On both themes `--bg` is now the base *under* the grain, not the colour of the page.**
`--px-ground` is what the eye sees, and outlined pixel elements fill with that. Filling one with
`--bg` puts a visibly darker sticker on the page — that is exactly how the theme toggle looked
before this. Measured, in case a dial is ever touched again: dark ground `#23221e` at σ 17.7, text
12.63:1, rules 1.31:1; light ground `#e8e3d4` at σ 16.4, text 12.85:1, muted 4.73:1, rules 1.24:1.
Note the muted value — the *old* off-white palette was at 4.39:1, below AA, and nobody had
measured it.

**`.post-content img` gets a light warm knock-back, not a duotone.** It was a duotone, and that was
a mistake worth recording: the images in these posts are evidence, not mood. One caption reads
"VS Code Dracula theme with Monaspace Neon font", and a duotone destroys exactly what the caption
points at. Revealing the original on hover did not save it — a tinted image carries no affordance
saying "hover me", and touch screens have no hover, so phones and laptops were being shown
different sites. The real problem was narrower and the aged paper made it worse: screenshots carry
white UI chrome and white punches holes in a cream ground. `sepia(.18) saturate(.92)
brightness(.98)` seats them in the paper and keeps every pixel of information.

### Storage: local disk only

`settings.py` defines a single `STORAGES` dict (Django 5.1+ API): `STORAGES["default"]` is always `FileSystemStorage` (`MEDIA_ROOT = BASE_DIR/media`, `MEDIA_URL = /media/`); `STORAGES["staticfiles"]` is WhiteNoise's `CompressedManifestStaticFilesStorage` (content-hashed filenames, gzip precompression — `collectstatic` must run before every deploy).

**There is no S3 any more.** The site used to switch backends on a `USE_S3` env flag; that bucket was deleted in August 2026, the 26 files were restored to local disk, and the flag, the `AWS_*` settings, `boto3` and `django-storages` were all removed. Post bodies holding absolute bucket URLs were rewritten by `python manage.py rewrite_media_urls` (idempotent, `--dry-run` available; `website_app/media_urls.py` keeps the legacy prefix as a deliberate hardcoded literal). Migrations `website_app/0005`/`0006` were rewritten so migration history no longer imports the S3 backend — `storage` is not a database-level attribute, so the schema is unchanged. Do not re-add a per-field storage argument: `STORAGES["default"]` is the only mechanism.

`media/` is **tracked in git** — those files are already served publicly, so tracking them leaks nothing, and it is their offsite backup now that S3 is gone. A fresh clone (and every deploy, which is a `git pull`) gets working media. `MediaFile.save()` logs storage diagnostics via `logging` (`website_app.models`), not `print()`.

In production Nginx serves `/media/` and `/static/` straight from disk — the `static(settings.MEDIA_URL, ...)` call in `urls.py` returns `[]` whenever `DEBUG` is False, so it is a dev-only helper. **The public domain reaches the site through Nginx too**: the cloudflared tunnel points at `127.0.0.1:80`, not at Gunicorn. If it is ever pointed back at `:8000`, `/media/` will 404 publicly while still working over LAN, because WhiteNoise serves `STATIC_ROOT` only.

`tools.js`'s alarm sound and any other static asset must be referenced via `{% static %}` (or read from a `data-*` attribute populated by `{% static %}`, see `tools/templates/tools/tools.html`) — a hardcoded `/static/...` path breaks once manifest hashing renames the file.

### Database

`DATABASE_URL` present → Postgres via `dj_database_url`, with `ssl_require` auto-disabled for `localhost`/`127.0.0.1` (the Pi talks to a local Postgres). Absent → SQLite at `db.sqlite3`. `db.sqlite3` and `data.json` are gitignored; `scripts/migrate.py` loads `data.json` if present, skipping the load step otherwise.

### Admin and TinyMCE

The real admin lives at `settings.ADMIN_URL` from the env; `/admin/` is a decoy route mapped to `website_app.views.fadmin`, which renders the 404 page. Post bodies are TinyMCE `HTMLField`s rendered with `|safe`.

To embed media in a post, the file must first exist as a `MediaFile` in admin: `TINYMCE_DEFAULT_CONFIG` points `image_list`/`media_list` at `/media-list/?type=image|audio` (the only two `MediaFile.MEDIA_TYPE_CHOICES`), served by the `media_list` view, gated with `staff_member_required_or_404` (`website_project/decorators.py`) rather than Django's own `staff_member_required` — the latter redirects anonymous users to the admin login page, leaking `settings.ADMIN_URL` via the `Location` header.

**TinyMCE preserves inline colour *and* inline background, and pasted markup brings both.**
The background half was found by rendering the real production posts rather than the dev
fixtures: `event-management-system` highlights its headings with
`background-color: rgb(191, 237, 210)`, a pale mint picked when the site had only a light theme
and within a hair of `--mark`. On the dark ground the band stays pale while the surrounding text
turned ivory, so whole headings vanish into their own highlight. `.post-content
[style*="background-color"]` puts ink back on top via `--on-highlight`, which is defined once in
`:root` and **deliberately not redefined in either dark block** — the pasted background does not
change with the theme, so the ink on it must not either. That rule has to sit *after* the inline
colour rules below, because a span can carry both and the later `!important` wins.

 A stored
`color: rgb(0, 0, 0)` is black text on the dark ground. `.post-content` neutralises inline black
and white with `color: inherit !important` — narrowly, so a deliberately coloured word still
works; inline styles lose to nothing else. Pasted content also arrives with foreign wrappers
(ChatGPT `<div>`s carrying Tailwind classes, `data-start`/`data-end` attributes). Those are inert
here, but a code block pasted that way arrives as a plain `div` and never gets `pre` styling —
CSS cannot recover semantics that were never pasted. `.post-content` styles everything the
toolbar can emit, including lists, tables and `codesample`, which no current post uses yet.

`debug_toolbar` and `django_extensions` are dev-only (`requirements-dev.txt`, not installed in prod) — both `INSTALLED_APPS`/`MIDDLEWARE` entries and the `import debug_toolbar` in `urls.py` are gated behind `if DEBUG`. Production always runs `DEBUG=False`.

## Deployment

Self-hosted on a Raspberry Pi 4: Nginx → Gunicorn under a `django-website` systemd unit (`sudo systemctl restart django-website`), Postgres local. Step-by-step guides live in `deployment/` — note that directory and `media_for_blogposts/` are **gitignored and local-only**, so they won't appear on a fresh clone.

`.github/workflows/ping.yml` curls `https://pflaumax.dev/healthcheck/` every 10 minutes; `/healthcheck/` is `@csrf_exempt` (no `@require_GET` — HEAD requests must pass too) and excluded from page-view stats.
