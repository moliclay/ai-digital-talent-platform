(async () => {
  const button = document.querySelector('button[class*="nameButton"]');
  if (!button) return 'no-trigger';
  button.click();
  await new Promise((r) => setTimeout(r, 700));
  return JSON.stringify({ modal: Boolean(document.querySelector('[role="dialog"]')) });
})()
