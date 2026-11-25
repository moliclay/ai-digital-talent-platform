(async () => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const setInput = (selector, value) => {
    const input = document.querySelector(selector);
    if (!input) return false;
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(input, value);
    input.dispatchEvent(new Event('input', { bubbles: true }));
    return true;
  };
  setInput('#username', 'hr_zhao');
  setInput('#password', 'wrong-password');
  await wait(200);
  const submit = [...document.querySelectorAll('button')].find((el) => el.getAttribute('type') === 'submit');
  if (!submit) return 'no-submit';
  submit.click();
  await wait(1800);
  return document.body.innerText.includes('账号或密码不对') ? 'error-shown' : 'no-error';
})()
