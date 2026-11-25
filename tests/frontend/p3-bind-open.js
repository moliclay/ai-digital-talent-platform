(async () => {
  const button = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '绑定测评');
  if (!button) return 'no-button';
  button.click();
  await new Promise((r) => setTimeout(r, 900));
  return JSON.stringify({ dialog: document.body.innerText.includes('选择一份试卷和候选人'), rows: document.querySelectorAll('input[type="checkbox"]').length });
})()
