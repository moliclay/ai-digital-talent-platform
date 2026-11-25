(() => {
  const out = [];
  for (const text of ['处理下一份','合格线 70','未过']) {
    const el = [...document.querySelectorAll('main *')].find((n) => n.children.length === 0 && (n.innerText || '').trim() === text);
    if (!el) { out.push({ text, missing: true }); continue; }
    out.push({ text, tag: el.tagName, cls: String(el.className), parent: String(el.parentElement?.className), disabled: el.disabled ?? el.closest('button')?.disabled ?? false });
  }
  return JSON.stringify(out);
})()
