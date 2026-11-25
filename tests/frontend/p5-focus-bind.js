(async () => {
  const trigger = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '绑定测评');
  if (!trigger) return JSON.stringify({ step: 'no-trigger' });
  trigger.focus(); trigger.click();
  await new Promise((r) => setTimeout(r, 700));
  const dialog = document.querySelector('[role="dialog"]');
  const inside = Boolean(dialog && dialog.contains(document.activeElement));
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }));
  await new Promise((r) => setTimeout(r, 500));
  return JSON.stringify({ opened: Boolean(dialog), focusInside: inside, closed: !document.querySelector('[role="dialog"]'), focusReturned: document.activeElement === trigger });
})()
