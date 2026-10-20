// Run via claude-in-chrome javascript_tool on https://www.instagram.com/<handle>/reels/ (logged-in Chrome).
// Scrolls until >= WANT reels are loaded, returns TSV "<url>\t<views as shown>" lines for ig_fetch.py index.
// The anchor's own text is the view count, in the browser's locale (e.g. "60,6 N", "1.918", "1,2 Tr", "12.5K").
const WANT = 30;
const seen = new Map();
const grab = () => {
  for (const a of document.querySelectorAll('a[href*="/reel/"]')) {
    const m = a.getAttribute('href').match(/\/reel\/([^/?]+)/);
    if (m && !seen.has(m[1])) seen.set(m[1], a.innerText.trim().split('\n')[0]);
  }
};
await new Promise((r) => setTimeout(r, 2000));
for (let i = 0, last = -1; i < 15 && seen.size < WANT; i++) {
  grab();
  if (seen.size === last) break;
  last = seen.size;
  window.scrollBy(0, 4000);
  await new Promise((r) => setTimeout(r, 1800));
}
grab();
[...seen].slice(0, WANT).map(([id, v]) => `https://www.instagram.com/reel/${id}/\t${v}`).join('\n');
