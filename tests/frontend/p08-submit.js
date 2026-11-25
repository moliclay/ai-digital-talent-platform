(async () => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const setValue = (el, value) => {
    const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value").set;
    setter.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
  };

  const name = document.querySelector("#candidate");
  if (name) setValue(name, "张伟");
  await sleep(150);

  const clickLabel = (text) => {
    const labels = [...document.querySelectorAll("label")];
    for (const label of labels) {
      const input = label.querySelector("input");
      if (input && !input.checked && label.textContent.includes(text)) label.click();
    }
  };

  ["PyTorch", "TensorFlow", "先确认对方担心的具体风险点", "哪一步可以复用或改流程", "链路追踪与慢查询", "拆解线索质量与转化漏斗"].forEach(clickLabel);

  const essay = document.querySelector("textarea");
  if (essay) setValue(essay, "Q/K/V、缩放点积、多头注意力");

  await sleep(300);
  const submit = [...document.querySelectorAll("button")].find((b) => b.textContent.trim() === "交卷");
  if (submit) submit.click();
  await sleep(600);
  const confirm = [...document.querySelectorAll("button")].find((b) => b.textContent.trim() === "确定交卷");
  if (confirm) confirm.click();
  await sleep(6000);

  return {
    h1: document.querySelector("h1")?.textContent ?? "",
    text: document.body.innerText.slice(0, 900),
  };
})()
