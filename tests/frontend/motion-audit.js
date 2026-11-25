(() => {
  const items = document.getAnimations().map((a) => {
    const t = a.effect?.getTiming?.() ?? {};
    return { name: a.animationName ?? a.id ?? 'transition', delay: t.delay, duration: t.duration, fill: t.fill, play: a.playState };
  });
  return JSON.stringify({ reduce: matchMedia('(prefers-reduced-motion: reduce)').matches, count: items.length, items: items.slice(0, 20) });
})()
