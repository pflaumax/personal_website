# Monaspace Neon (variable, subset)

`MonaspaceNeonVar-subset.woff2` — 59 KB, axes `wght 200..800` and `slnt -11..0`.

Source: <https://github.com/githubnext/monaspace> release **v1.400**, asset
`monaspace-webfont-variable-v1.400.zip`, file `Variable Web Fonts/Monaspace Neon/Monaspace Neon Var.woff2`
(510 KB unmodified). Licence: SIL OFL 1.1, see `LICENSE.txt` — self-hosting is permitted.

## Rebuilding the subset

The upstream file is 510 KB because it carries 2460 glyphs and a `wdth` axis this site never
varies. Pinning the width and cutting to the scripts actually used brings it to 59 KB, which is
still one fifth of the single-weight `MonaspaceNeonFrozen-ExtraLight.ttf` it replaced.

```bash
pip install "fonttools[woff]" brotli

fonttools varLib.instancer "Monaspace Neon Var.woff2" wdth=100 -o pin.ttf

pyftsubset pin.ttf --flavor=woff2 --output-file=MonaspaceNeonVar-subset.woff2 \
  --unicodes="U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,\
U+0300-0301,U+2000-206F,U+2070,U+2074,U+20AC,U+2122,U+2190-21FF,U+2212,U+2215,\
U+2500-259F,U+25A0-25CF,U+2713,U+2717,U+2605,U+FEFF,U+FFFD"
```

The ranges cover Latin-1, punctuation, arrows, box drawing and geometric shapes — the last two
because posts about terminal tooling paste them. Anything outside the subset still renders:
the stack falls through to `'Courier New', Courier, monospace` per character, so a stray glyph
comes out in the fallback rather than as tofu. If posts start using a script that is not
covered, widen `--unicodes` and rebuild rather than shipping the 510 KB original.
