(async () => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const box = document.querySelector('#ledger-candidate');
  if (!box) return 'no-select';
  box.click();
  await wait(200);
  const option = [...document.querySelectorAll('[role="option"]')].find((el) => el.textContent.trim() === '陈宇');
  if (!option) return 'no-option';
  option.click();
  await wait(1800);
  return document.body.innerText.includes('prejob_assessment') || document.body.innerText.includes('课后考核') ? 'ledger-chenyu' : 'empty';
})()
