(() => {
  const panel = document.querySelector('section[aria-labelledby="login-title"] > div');
  const preview = document.querySelector('[class*="preview"]');
  const input = document.querySelector('#username');
  const read = (el) => {
    if (!el) return null;
    const s = getComputedStyle(el);
    return {
      bg: s.backgroundImage !== 'none' ? s.backgroundImage.slice(0, 120) : s.backgroundColor,
      border: `${s.borderTopWidth} ${s.borderTopColor}`,
      radius: s.borderRadius,
      shadow: s.boxShadow.slice(0, 160),
      blur: s.backdropFilter,
    };
  };
  return JSON.stringify({ panel: read(panel), preview: read(preview), input: read(input) });
})()
