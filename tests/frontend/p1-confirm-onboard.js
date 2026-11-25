(async () => {
  const confirm = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '确认转正');
  if (!confirm) return 'missing-confirm';
  confirm.click();
  await new Promise((resolve) => setTimeout(resolve, 2800));
  return JSON.stringify({
    success: document.body.innerText.includes('员工账号已创建'),
    passwordField: Boolean(document.querySelector('#onboard-password')),
    accountField: Boolean(document.querySelector('#onboard-account')),
    employeeBadge: document.body.innerText.includes('已转正式员工'),
  });
})()
