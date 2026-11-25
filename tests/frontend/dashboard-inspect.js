(() => {
  const card = document.querySelector('[class*="statCard"]');
  const cards = [...document.querySelectorAll('[class*="statCard"]')].map(el => { const s=getComputedStyle(el); return {bg:s.backgroundImage !== 'none' ? s.backgroundImage.slice(0,80) : s.backgroundColor, border:s.borderTopColor, w:Math.round(el.getBoundingClientRect().width)}; });
  const root = document.querySelector('.glass-app');
  return JSON.stringify({ cards, root: root ? {bg:getComputedStyle(root).backgroundImage.slice(0,50)} : null });
})()
