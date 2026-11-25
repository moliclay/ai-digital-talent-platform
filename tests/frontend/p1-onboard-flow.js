(async () => {
  const open = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '转为正式员工');
  if (!open) return 'missing-open';
  open.click();
  await new Promise((resolve) => setTimeout(resolve, 500));
  const confirm = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '确认转正');
  if (!confirm) return 'missing-confirm';
  confirm.click();
  await new Promise((resolve) => setTimeout(resolve, 3000));
  return JSON.stringify({
    success: document.body.innerText.includes('员工账号已创建'),
    passwordField: Boolean(document.querySelector('#onboard-password')),
    accountField: Boolean(document.querySelector('#onboard-account')),
  });
})()
