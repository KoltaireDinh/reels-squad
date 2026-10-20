// Watch a reel frame by frame in Chrome (claude-in-chrome).
// 1. navigate to https://www.instagram.com/p/<id>/embed/   (embed = exactly one video, no feed auto-advance)
// 2. javascript_tool: run this whole file once. It lifts the video into a full-viewport stage with a timecode.
// 3. Then per moment:  await watch.seek(3.5)  -> screenshot (timecode top-left says which moment you see)
//    Real-time look at motion: await watch.play(2, 6), audio: watch.unmute()
//    GIF: gif_creator only captures screenshots taken as standalone `computer` calls, not inside browser_batch.
//    watch.info() -> {duration, width, height}
await (async () => {
  const v = document.querySelector('video');
  if (!v) return 'no <video> on this page — is it the /embed/ URL of a video post?';
  v.muted = true; v.preload = 'auto'; v.playsInline = true;
  if (!(v.readyState >= 1)) { v.load(); await new Promise((r, j) => { v.addEventListener('loadedmetadata', r, { once: true }); setTimeout(() => j(new Error('metadata timeout')), 15000); }); }

  // Stage: black full-viewport layer with only the video, so IG overlays never cover frames.
  const stage = document.createElement('div');
  stage.style.cssText = 'position:fixed;inset:0;z-index:2147483646;background:#000;display:flex;align-items:center;justify-content:center';
  const tc = document.createElement('div');
  tc.style.cssText = 'position:fixed;top:6px;left:6px;z-index:2147483647;background:#000c;color:#ffd84a;font:700 20px ui-monospace,monospace;padding:2px 8px;border-radius:4px';
  // A visible <video> is a hardware overlay layer that makes CDP screenshots hang, so the frame is
  // mirrored onto a <canvas> and the video itself is kept invisible (still decoding).
  const cv = document.createElement('canvas');
  cv.width = v.videoWidth; cv.height = v.videoHeight;
  cv.style.cssText = 'height:100vh;width:auto;max-width:100vw;object-fit:contain;display:block';
  const ctx = cv.getContext('2d');
  v.style.cssText = 'position:fixed;left:0;top:0;width:2px;height:2px;opacity:0;pointer-events:none';
  v.controls = false;
  stage.append(cv);
  document.body.append(stage, tc, v);
  const paint = () => {
    ctx.drawImage(v, 0, 0, cv.width, cv.height);
    tc.textContent = `${v.currentTime.toFixed(2)}s / ${v.duration.toFixed(2)}s`;
  };
  v.addEventListener('timeupdate', paint);
  v.addEventListener('seeked', paint);

  const frameShown = () => new Promise((r) => (v.requestVideoFrameCallback ? v.requestVideoFrameCallback(() => r()) : setTimeout(r, 80)));
  window.watch = {
    async seek(t) {
      v.pause();
      const target = Math.max(0, Math.min(t, v.duration - 0.001));
      const shown = frameShown();
      v.currentTime = target;
      await new Promise((r) => v.addEventListener('seeked', r, { once: true }));
      await Promise.race([shown, new Promise((r) => setTimeout(r, 300))]);
      paint();
      return +v.currentTime.toFixed(3);
    },
    async play(from = 0, to = v.duration) {
      await this.seek(from);
      await v.play();
      await new Promise((r) => { const tick = () => { paint(); v.currentTime >= to || v.paused ? r() : requestAnimationFrame(tick); }; tick(); });
      v.pause(); paint();
    },
    unmute() { v.muted = false; v.volume = 1; },
    info() { return { duration: v.duration, width: v.videoWidth, height: v.videoHeight }; },
  };
  await window.watch.seek(0);
  return JSON.stringify(window.watch.info());
})();
