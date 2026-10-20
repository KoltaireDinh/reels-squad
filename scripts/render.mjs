// Deterministic HTML -> MP4 renderer for reels builds.
// The page is never recorded in real time: every frame is seeked to an exact time and screenshotted,
// so slow machines never drop frames.
//
// Page contract (in the build's index.html):
//   window.REEL = { width: 1080, height: 1920, fps: 30, duration: <seconds>,
//                   ready?: Promise, seek: (t) => void | Promise }
// CSS animations / Web Animations are also paused and seeked to t automatically,
// and a GSAP global timeline is seeked if window.gsap exists.
//
// Usage:
//   node tools/render.mjs <build/index.html> <out.mp4> [--audio a.mp3] [--from 0] [--to 5] [--fps 30]
//   node tools/render.mjs <build/index.html> --stills <dir> [--every 1]   (PNG stills for review)

import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { createReadStream, existsSync, mkdirSync, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { dirname, extname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml', '.webp': 'image/webp', '.gif': 'image/gif',
  '.woff': 'font/woff', '.woff2': 'font/woff2', '.ttf': 'font/ttf', '.otf': 'font/otf', '.glb': 'model/gltf-binary', '.gltf': 'model/gltf+json',
  '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.mp4': 'video/mp4' };

function serve(root) {
  const server = createServer((req, res) => {
    const file = resolve(root, '.' + decodeURIComponent(new URL(req.url, 'http://x').pathname));
    if (!file.startsWith(root) || !existsSync(file) || statSync(file).isDirectory()) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { 'Content-Type': MIME[extname(file).toLowerCase()] || 'application/octet-stream' });
    createReadStream(file).pipe(res);
  });
  server.unref();
  return new Promise((ok) => server.listen(0, '127.0.0.1', () => ok(`http://127.0.0.1:${server.address().port}`)));
}
const argv = process.argv.slice(2);
const opt = (name, dflt) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 ? argv[i + 1] : dflt;
};
const positional = argv.filter((a, i) => !a.startsWith('--') && !(i > 0 && argv[i - 1].startsWith('--')));
const [htmlArg, outArg] = positional;
if (!htmlArg) {
  console.error('usage: node render.mjs <index.html> <out.mp4> [--audio f] [--from s] [--to s] | --stills <dir> [--every s]');
  process.exit(2);
}
const stillsDir = opt('stills');
const ffmpeg = process.env.FFMPEG || (existsSync(join(here, 'bin', 'ffmpeg.exe')) ? join(here, 'bin', 'ffmpeg.exe') : 'ffmpeg');

const browser = await chromium.launch({ args: ['--disable-gpu-vsync', '--force-color-profile=srgb', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  // Under memory pressure Chromium can drop the WebGL context and keep rendering black frames silently.
  await page.addInitScript(() => {
    window.__glLost = 0;
    addEventListener('webglcontextlost', () => { window.__glLost++; }, true);
  });

  // file:// blocks ES modules, so serve the workspace (parent of tools/) over localhost.
  const root = resolve(here, '..');
  const rel = relative(root, resolve(htmlArg));
  const url = rel.startsWith('..') ? pathToFileURL(resolve(htmlArg)).href : `${await serve(root)}/${rel.split(sep).join('/')}`;
  await page.goto(url, { waitUntil: 'load' });
  await page.waitForFunction(() => window.REEL && typeof window.REEL.seek === 'function', null, { timeout: 15000 })
    .catch(() => { throw new Error(`window.REEL.seek not found. Page errors: ${errors.join(' | ') || 'none'}`); });
  const meta = await page.evaluate(async () => {
    await window.REEL.ready;
    await document.fonts.ready;
    const r = window.REEL;
    return { width: r.width || 1080, height: r.height || 1920, fps: r.fps || 30, duration: r.duration };
  });
  if (!meta.duration) throw new Error('window.REEL.duration missing');
  await page.setViewportSize({ width: meta.width, height: meta.height });

  const fps = Number(opt('fps', meta.fps));
  const from = Number(opt('from', 0));
  const to = Math.min(Number(opt('to', meta.duration)), meta.duration);

  const seek = (t) => page.evaluate(async (t) => {
    for (const a of document.getAnimations()) { a.pause(); a.currentTime = t * 1000; }
    if (window.gsap) { window.gsap.globalTimeline.pause(); window.gsap.globalTimeline.time(t); }
    await window.REEL.seek(t);
    // Two rAFs so canvas/WebGL content for this time is actually on screen.
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    return window.__glLost;
  }, t).then((lost) => {
    if (lost) throw new Error(`WebGL context lost at t=${t.toFixed(2)}s (low memory?). Re-render this range in a smaller --from/--to chunk.`);
  });

  if (stillsDir) {
    mkdirSync(stillsDir, { recursive: true });
    const every = Number(opt('every', 1));
    for (let t = from; t <= to + 1e-9; t += every) {
      await seek(t);
      const file = join(stillsDir, `t${t.toFixed(2).padStart(6, '0')}.png`);
      await page.screenshot({ path: file });
      console.log(file);
    }
  } else {
    if (!outArg) throw new Error('missing <out.mp4>');
    mkdirSync(dirname(resolve(outArg)), { recursive: true });
    const audio = opt('audio');
    const args = ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-i', '-'];
    if (audio) args.push('-ss', String(from), '-i', audio, '-map', '0:v', '-map', '1:a', '-c:a', 'aac', '-b:a', '192k', '-shortest');
    args.push('-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', String(fps), '-movflags', '+faststart', resolve(outArg));
    const ff = spawn(ffmpeg, args, { stdio: ['pipe', 'inherit', 'inherit'] });
    const done = new Promise((ok, fail) => ff.on('close', (c) => (c === 0 ? ok() : fail(new Error(`ffmpeg exited ${c}`)))));

    const total = Math.round((to - from) * fps);
    for (let i = 0; i < total; i++) {
      await seek(from + i / fps);
      const buf = await page.screenshot({ type: 'png' });
      if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
      if (i % fps === 0) process.stdout.write(`\rframe ${i}/${total}`);
    }
    ff.stdin.end();
    await done;
    console.log(`\nwrote ${outArg} (${meta.width}x${meta.height} @${fps}fps, ${(to - from).toFixed(2)}s)`);
  }
  if (errors.length) console.warn(`page errors:\n  ${errors.join('\n  ')}`);
} finally {
  await browser.close();
}
