(async () => {
  const open = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '绑定测评');
  if (!open) return 'no-open';
  open.click();
  await new Promise((r) => setTimeout(r, 900));
  const label = [...document.querySelectorAll('label')].find((el) => (el.innerText || '').includes('李娜'));
  if (!label) return 'no-candidate';
  const box = label.querySelector('input[type="checkbox"]');
  box.click();
  await new Promise((r) => setTimeout(r, 200));
  const confirm = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '确认绑定');
  if (!confirm) return 'no-confirm';
  confirm.click();
  await new Promise((r) => setTimeout(r, 1500));
  return JSON.stringify({ dialog: document.body.innerText.includes('选择一份试卷和候选人'), banner: document.body.innerText.includes('已绑定'), text: document.body.innerText.slice(-200) });
})()
