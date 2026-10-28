# Academic homepage maintenance

The public homepage is `index.html`. `publications.html`, `awards.html`, and `service.html` provide the complete archives. Static HTML is served directly by GitHub Pages; `.nojekyll` prevents the old template from generating a second homepage.

## Change content and rebuild

Run `python3 tools/build_site.py` from any directory. It uses the original publication, awards and service records in `content/profile-source.html`, plus the structured venue and journal data in `assets/`. The homepage introduction, selected-paper highlights, news and timeline are defined in `tools/build_site.py`. `assets/publications.json` is generated and should not be edited directly. Commit the rebuilt HTML and generated data with each source change.

- Styles and responsive layout: `assets/site.css`
- Publication filtering and metric refresh: `assets/site.js`
- Navigation research icon: `assets/purpleleaves-maple.png`
- Browser tab icons: `favicon.ico`, `assets/favicon-purpleleaves-32.png`; Apple touch icon: `assets/apple-touch-icon-purpleleaves.png`
- Venue colors and assignments: `assets/venue-groups.json`
- Verified static metric fallbacks: `assets/scholar-metrics.json`, `assets/journal-metrics.json`

## Automatic metrics

GitHub Actions updates Google Scholar daily at approximately 16:17 Asia/Shanghai. Annual journal metrics run on July 3 and 17 at approximately 16:37 Asia/Shanghai. Scheduled runs may be delayed by GitHub. Both workflows can be run manually from Actions.

Both jobs write to the existing `google-scholar-stats` branch using a shared concurrency group and normal pushes. The browser reads the newer validated snapshot; if a request fails, the latest verified data remains visible. Scholar and publisher websites may block automated requests; check Actions failures before changing any numbers. Never label CiteScore, five-year IF or a forecast as the annual Journal Impact Factor.

A workflow needs repository Actions enabled and permission to write contents. No paid Clarivate API key is required for the current publisher/LetPub implementation. No credentials should be committed.

## Publishing and rollback

The intended Pages source is `main` / repository root. Confirm the configured source under Settings > Pages. Changes to `main` should rebuild the site using that configuration. Check the Pages deployment result and the live URL after publishing. Use `git revert <commit>` for a recoverable rollback; do not rewrite repository history.

The original theme, images and documents are retained for reference and existing direct links. Their Markdown homepage is not used while `.nojekyll` is present. Repository ownership and account access remain with the owner; maintenance does not require transferring the account or sharing a password.
