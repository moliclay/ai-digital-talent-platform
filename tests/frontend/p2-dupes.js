(async () => {
  const tab = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '简历查重');
  if (!tab) return 'no-tab';
  tab.click();
  await new Promise((r) => setTimeout(r, 500));
  const combobox = document.querySelector('#semantic-threshold');
  if (!combobox) return 'no-threshold';
  combobox.click();
  await new Promise((r) => setTimeout(r, 200));
  const option = [...document.querySelectorAll('[role="option"]')].find((el) => el.textContent.includes('0.50'));
  if (!option) return 'no-option';
  option.click();
  await new Promise((r) => setTimeout(r, 2400));
  return JSON.stringify({ pairs: document.querySelectorAll('tbody tr').length, text: document.body.innerText.includes('张伟') });
})()
