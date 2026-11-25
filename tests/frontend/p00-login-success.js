(async () => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const account = [...document.querySelectorAll('button')].find((el) => (el.getAttribute('aria-label') || '').includes('hr_zhao'));
  if (!account) return 'no-account';
  account.click();
  await wait(250);
  const submit = [...document.querySelectorAll('button')].find((el) => el.getAttribute('type') === 'submit');
  if (!submit) return 'no-submit';
  submit.click();
  await wait(2200);
  return location.pathname;
})()
