(() => {
  const tag = document.querySelector('[class*="tag"]');
  const title = document.querySelector('[class*="title"]');
  const panel = document.querySelector('[class*="panelWrap"]');
  const pick = (el) => el ? { opacity: getComputedStyle(el).opacity, transform: getComputedStyle(el).transform, anim: getComputedStyle(el).animationName, delay: getComputedStyle(el).animationDelay, dur: getComputedStyle(el).animationDuration, fill: getComputedStyle(el).animationFillMode } : null;
  return JSON.stringify({ reduce: matchMedia('(prefers-reduced-motion: reduce)').matches, tag: pick(tag), title: pick(title), panel: pick(panel) });
})()
