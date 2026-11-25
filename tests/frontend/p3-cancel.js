(async () => {
  const cancel = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '取消' && el.closest('tbody'));
  if (!cancel) return 'no-cancel';
  cancel.click();
  await new Promise((r) => setTimeout(r, 600));
  const buttons = [...document.querySelectorAll('[role="dialog"] button')];
  const confirm = buttons[buttons.length - 1];
  if (!confirm) return 'no-confirm';
  confirm.click();
  await new Promise((r) => setTimeout(r, 1500));
  return JSON.stringify({ banner: document.body.innerText.includes('已取消这条测评任务'), text: document.body.innerText.slice(0, 450) });
})()
