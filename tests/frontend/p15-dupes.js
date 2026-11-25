(async () => {
  const combobox = document.querySelector('#semantic-threshold');
  if (!combobox) return 'no-combobox';
  combobox.click();
  await new Promise((r) => setTimeout(r, 200));
  const option = [...document.querySelectorAll('[role="option"]')].find((el) => el.textContent.includes('0.50'));
  if (!option) return 'no-option';
  option.click();
  await new Promise((r) => setTimeout(r, 20000));
  return document.body.innerText.includes('陈宇') ? 'threshold-05' : 'no-pairs';
})()
