(async () => {
  const trigger = document.querySelector('button[class*="nameButton"]');
  if (!trigger) return JSON.stringify({ step: 'no-trigger' });
  trigger.focus();
  trigger.click();
  await new Promise((r) => setTimeout(r, 700));
  const dialog = document.querySelector('[role="dialog"]');
  const inside = Boolean(dialog && dialog.contains(document.activeElement));
  const ariaModal = dialog?.getAttribute('aria-modal') ?? '';
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }));
  await new Promise((r) => setTimeout(r, 500));
  return JSON.stringify({
    dialogOpened: Boolean(dialog),
    focusInside: inside,
    ariaModal,
    closed: !document.querySelector('[role="dialog"]'),
    focusReturned: document.activeElement === trigger,
    focusText: (document.activeElement?.innerText || '').trim().slice(0, 12),
  });
})()
