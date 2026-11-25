(async () => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const click = (label) => {
    const button = [...document.querySelectorAll('button')].find((el) => el.textContent.trim() === label);
    if (button) button.click();
    return Boolean(button);
  };
  click('开始诊断');
  await wait(1400);
  const opened = click('生成培养计划');
  await wait(600);
  return opened && document.body.innerText.includes('周期（周）') ? 'generate-modal-open' : 'no-modal';
})()
