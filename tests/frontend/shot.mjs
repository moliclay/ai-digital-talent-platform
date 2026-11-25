#!/usr/bin/env node
/**
 * 用 Chrome DevTools Protocol 截图，避免依赖 Hermes 内置浏览器。
 * 用法：node tests/frontend/shot.mjs <url> <width> <height> <out.png> [--theme dark|light] [--dpr 1|2]
 */
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const args = process.argv.slice(2);
const [url, widthArg, heightArg, outArg] = args;
if (!url || !widthArg || !heightArg || !outArg) {
  console.error("usage: node tests/frontend/shot.mjs <url> <width> <height> <out.png> [--theme dark|light] [--dpr 1|2]");
  process.exit(1);
}
const flag = (name, fallback) => {
  const index = args.indexOf(`--${name}`);
  return index >= 0 ? args[index + 1] : fallback;
};
const theme = flag("theme", "dark");
const dpr = Number(flag("dpr", "1"));
const width = Number(widthArg);
const height = Number(heightArg);

const chromeCandidates = [
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
];
const chrome = chromeCandidates.find((candidate) => fs.existsSync(candidate));
if (!chrome) {
  console.error("找不到 Chrome 或 Edge");
  process.exit(1);
}

const port = 9400 + Math.floor(Math.random() * 400);
const profile = fs.mkdtempSync(path.join(os.tmpdir(), "cdp-shot-"));
const child = spawn(
  chrome,
  [
    "--headless=new",
    "--disable-gpu",
    "--hide-scrollbars",
    "--no-first-run",
    "--no-default-browser-check",
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    "about:blank",
  ],
  { stdio: "ignore" },
);

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function waitForDevtools() {
  for (let i = 0; i < 60; i += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (response.ok) return response.json();
    } catch {
      // 还没起来
    }
    await sleep(150);
  }
  throw new Error("DevTools 端口没有就绪");
}

function connect(wsUrl) {
  const socket = new WebSocket(wsUrl);
  let nextId = 1;
  const pending = new Map();
  const waiters = new Map();

  socket.addEventListener("message", (event) => {
    const message = JSON.parse(String(event.data));
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) reject(new Error(message.error.message));
      else resolve(message.result);
      return;
    }
    if (message.method && waiters.has(message.method)) {
      const list = waiters.get(message.method);
      waiters.delete(message.method);
      for (const resolve of list) resolve(message.params);
    }
  });

  const ready = new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, { once: true });
    socket.addEventListener("error", reject, { once: true });
  });

  function send(method, params = {}) {
    const id = nextId++;
    return new Promise((resolve, reject) => {
      pending.set(id, { resolve, reject });
      socket.send(JSON.stringify({ id, method, params }));
    });
  }

  function event(name) {
    return new Promise((resolve) => {
      const list = waiters.get(name) ?? [];
      list.push(resolve);
      waiters.set(name, list);
    });
  }

  return { ready, send, event, close: () => socket.close() };
}

try {
  await waitForDevtools();
  const created = await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent("about:blank")}`, {
    method: "PUT",
  }).then((response) => response.json());
  const page = connect(created.webSocketDebuggerUrl);
  await page.ready;

  await page.send("Page.enable");
  await page.send("Runtime.enable");

  if (flag("reduce", "")) {
    await page.send("Emulation.setEmulatedMedia", {
      features: [{ name: "prefers-reduced-motion", value: "reduce" }],
    });
  }

  const block = flag("block", "");
  if (block) {
    await page.send("Network.enable");
    await page.send("Network.setBlockedURLs", { urls: [`*${block}*`] });
  }

  await page.send("Emulation.setDeviceMetricsOverride", {
    width,
    height,
    deviceScaleFactor: dpr,
    mobile: width < 640,
  });

  const loaded = page.event("Page.loadEventFired");
  await page.send("Page.navigate", { url });
  await loaded;
  await sleep(Number(flag("settle", "1800")));

  if (theme === "light" || theme === "dark") {
    await page.send("Runtime.evaluate", {
      expression: `localStorage.setItem('tl.theme', '${theme}')`,
    });
    const reloaded = page.event("Page.loadEventFired");
    await page.send("Page.reload", { ignoreCache: false });
    await reloaded;
    await sleep(900);
  }

  if (flag("flow", "") === "theme") {
    await page.send("Runtime.evaluate", {
      expression: `(() => {
        const before = document.documentElement.dataset.theme;
        const button = document.querySelector('button[aria-label^="切换到"]');
        if (button) button.click();
        return before;
      })()`,
      returnByValue: true,
    });
    await sleep(500);
    const after = await page.send("Runtime.evaluate", {
      expression: `JSON.stringify({
        theme: document.documentElement.dataset.theme,
        label: document.querySelector('button[aria-label^="切换到"]')?.getAttribute('aria-label'),
        stored: localStorage.getItem('tl.theme')
      })`,
      returnByValue: true,
    });
    console.log("theme-toggle:", after.result.value);
  }

  const flow = flag("flow", "");
  if (flow === "login-bad" || flow === "login-empty" || flow === "login-long") {
    if (flow !== "login-empty") {
      await page.send("Runtime.evaluate", {
        expression: `(() => {
          const button = document.querySelector('button[aria-label="填入演示账号 hr_zhao"]');
          if (button) button.click();
          return Boolean(button);
        })()`,
        returnByValue: true,
      });
      await sleep(200);
    }
    if (flow === "login-bad") {
      await page.send("Runtime.evaluate", {
        expression: `(() => {
          const input = document.querySelector('input[name="password"]');
          const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
          setter.call(input, 'wrong-pass');
          input.dispatchEvent(new Event('input', { bubbles: true }));
          return input.value;
        })()`,
        returnByValue: true,
      });
    }
    if (flow === "login-long") {
      await page.send("Runtime.evaluate", {
        expression: `(() => {
          const input = document.querySelector('input[name="username"]');
          const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
          setter.call(input, 'x'.repeat(70));
          input.dispatchEvent(new Event('input', { bubbles: true }));
          return input.value.length;
        })()`,
        returnByValue: true,
      });
    }
    await page.send("Runtime.evaluate", {
      expression: `(() => { const form = document.querySelector('form'); form && form.requestSubmit(); return true; })()`,
    });
    await sleep(flow === "login-bad" ? 1500 : 400);
    const state = await page.send("Runtime.evaluate", {
      expression: `JSON.stringify({
        path: location.pathname,
        alert: document.querySelector('[role="alert"]')?.innerText ?? '',
        busy: document.querySelector('button[type="submit"]')?.getAttribute('aria-busy') ?? ''
      })`,
      returnByValue: true,
    });
    console.log("flow-state:", state.result.value);
  }

  if (flow === "login") {
    const demoUser = flag("user", "hr_zhao");
    const loginUsername = flag("loginUsername", "");
    const loginPassword = flag("loginPassword", "");
    if (loginUsername) {
      await page.send("Runtime.evaluate", {
        expression: `(() => {
          const setValue = (selector, value) => {
            const input = document.querySelector(selector);
            if (!input) return false;
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            setter.call(input, value);
            input.dispatchEvent(new Event('input', { bubbles: true }));
            return true;
          };
          return setValue('input[name="username"]', ${JSON.stringify(loginUsername)})
            && setValue('input[name="password"]', ${JSON.stringify(loginPassword)});
        })()`,
        returnByValue: true,
      });
    } else {
      await page.send("Runtime.evaluate", {
        expression: `(() => {
          const button = document.querySelector('button[aria-label="填入演示账号 ${demoUser}"]');
          if (button) button.click();
          return Boolean(button);
        })()`,
        returnByValue: true,
      });
    }
    await sleep(300);
    await page.send("Runtime.evaluate", {
      expression: `(() => {
        const form = document.querySelector('form');
        if (form) form.requestSubmit();
        return Boolean(form);
      })()`,
      returnByValue: true,
    });
    await sleep(4200);
    const pauseApi = flag("pauseApi", "");
    if (pauseApi) {
      await page.send("Fetch.enable", {
        patterns: [{ urlPattern: `*${pauseApi === "1" ? "api" : pauseApi}*` }],
      });
    }

    const apiDelay = Number(flag("apiDelay", "0"));
    if (apiDelay) {
      await page.send("Network.enable");
      await page.send("Network.emulateNetworkConditions", {
        offline: false,
        latency: apiDelay,
        downloadThroughput: -1,
        uploadThroughput: -1,
      });
    }

    const after = flag("after", "");
    if (after) {
      await page.send("Page.navigate", { url: `http://127.0.0.1:5174${after}` });
      await sleep(apiDelay ? 850 : Number(flag("afterWait", "3200")));
    }

    const postWidth = Number(flag("postWidth", "0"));
    if (postWidth) {
      await page.send("Emulation.setDeviceMetricsOverride", {
        width: postWidth,
        height: Number(flag("postHeight", heightArg)),
        deviceScaleFactor: dpr,
        mobile: postWidth < 640,
      });
      await sleep(900);
    }

    const clickText = flag("clickText", "");
    if (clickText) {
      await page.send("Runtime.evaluate", {
        expression: `(() => {
          const label = ${JSON.stringify(clickText)};
          const target = [...document.querySelectorAll('button')].find((el) => {
            const text = (el.innerText || '').trim();
            return text === label || text.startsWith(label);
          });
          if (target) { target.click(); return true; }
          return false;
        })()`,
        returnByValue: true,
      });
      await sleep(900);
    }

    const clickSelector = flag("clickSelector", "");
    if (clickSelector) {
      await page.send("Runtime.evaluate", {
        expression: `(() => {
          const el = document.querySelector(${JSON.stringify(clickSelector)});
          if (el) { el.click(); return true; }
          return false;
        })()`,
        returnByValue: true,
      });
      await sleep(1200);
    }

    const uploadFile = flag("upload", "");
    const uploadText = flag("uploadText", "开始上传");
    if (uploadFile) {
      const doc = await page.send("DOM.getDocument");
      const inputNode = await page.send("DOM.querySelector", {
        nodeId: doc.root.nodeId,
        selector: 'input[type="file"]',
      });
      if (inputNode.nodeId) {
        await page.send("DOM.setFileInputFiles", {
          files: [uploadFile],
          nodeId: inputNode.nodeId,
        });
        await sleep(400);
        await page.send("Runtime.evaluate", {
          expression: `(() => {
            const target = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === ${JSON.stringify(uploadText)});
            if (target) { target.click(); return true; }
            return false;
          })()`,
          returnByValue: true,
        });
        await sleep(4500);
      }
    }

    const clickWait = Number(flag("clickWait", "0"));
    if (clickWait > 0) await sleep(clickWait);

    const clickTextAfter = flag("clickTextAfter", "");
    if (clickTextAfter) {
      const clickedAfter = await page.send("Runtime.evaluate", {
        expression: `(() => {
          const label = ${JSON.stringify(clickTextAfter)};
          const target = [...document.querySelectorAll('button')].find((el) => {
            const text = (el.innerText || '').trim();
            return text === label || text.startsWith(label);
          });
          if (target) { target.click(); return true; }
          return false;
        })()`,
        returnByValue: true,
      });
      console.log("clickTextAfter:", clickTextAfter, clickedAfter.result.value);
      await sleep(900);
    }

    const search = flag("search", "");
    if (search) {
      await page.send("Runtime.evaluate", {
        expression: `(() => {
          const input = document.querySelector('#semantic-q') || document.querySelector('input[aria-label]');
          if (!input) return false;
          const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
          setter.call(input, ${JSON.stringify(search)});
          input.dispatchEvent(new Event('input', { bubbles: true }));
          const button = [...document.querySelectorAll('button')].find((el) => {
            const label = (el.innerText || '').trim();
            return label === '搜索' || label === '检索';
          });
          if (button) setTimeout(() => button.click(), 60);
          return Boolean(button);
        })()`,
        returnByValue: true,
      });
      await sleep(1600);
    }

    const extraWait = Number(flag("wait", "0"));
    if (extraWait > 0) await sleep(extraWait);

    const state = await page.send("Runtime.evaluate", {
      expression: `JSON.stringify({
        path: location.pathname,
        h1: document.querySelector('h1')?.textContent ?? '',
        text: document.body.innerText.slice(0, 220)
      })`,
      returnByValue: true,
    });
    console.log("flow:", state.result.value);

    const metrics = await page.send("Runtime.evaluate", {
      expression: `(() => {
        const root = document.querySelector('main') || document.body;
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        let chars = 0, small = 0, node;
        while ((node = walker.nextNode())) {
          const text = (node.textContent || '').trim();
          if (!text) continue;
          const el = node.parentElement;
          if (!el) continue;
          const size = parseFloat(getComputedStyle(el).fontSize);
          chars += text.length;
          if (size < 13) small += text.length;
        }
        const tinyTargets = [...document.querySelectorAll('button, a[href]')]
          .filter((el) => {
            const rect = el.getBoundingClientRect();
            return rect.width > 0 && (rect.width < 24 || rect.height < 24);
          })
          .map((el) => (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 12));
        return JSON.stringify({
          chars, small,
          smallPct: chars ? Math.round((small / chars) * 100) : 0,
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
          tinyTargets
        });
      })()`,
      returnByValue: true,
    });
    console.log("metrics:", metrics.result.value);
  }

  const scrollSelector = flag("scrollSelector", "");
  const scrollTop = Number(flag("scrollTop", "0")) || 0;
  if (scrollSelector) {
    await page.send("Runtime.evaluate", {
      expression: `(() => {
        const el = document.querySelector(${JSON.stringify(scrollSelector)});
        if (el) el.scrollTop = ${scrollTop};
      })()`,
    });
    await sleep(200);
  }

  const evalFile = flag("evalFile", "");
  if (evalFile) {
    const code = fs.readFileSync(evalFile, "utf8");
    const evaluated = await page.send("Runtime.evaluate", {
      expression: code,
      awaitPromise: true,
      returnByValue: true,
    });
    if (evaluated.exceptionDetails) throw new Error(evaluated.exceptionDetails.exception?.description || evaluated.exceptionDetails.text);
    console.log("eval:", JSON.stringify(evaluated.result?.value));
    await sleep(300);
  }

  const shot = await page.send("Page.captureScreenshot", { format: "png", fromSurface: true });
  fs.mkdirSync(path.dirname(outArg), { recursive: true });
  fs.writeFileSync(outArg, Buffer.from(shot.data, "base64"));

  const metrics = await page.send("Runtime.evaluate", {
    expression: `JSON.stringify({
      title: document.title,
      h1: document.querySelector('h1')?.textContent ?? '',
      theme: document.documentElement.dataset.theme,
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      scrollHeight: document.documentElement.scrollHeight,
      viewportHeight: window.innerHeight,
      overflow: [...document.querySelectorAll('*')].filter((el) => {
        const r = el.getBoundingClientRect();
        return r.right > document.documentElement.clientWidth + 0.5;
      }).slice(0, 6).map((el) => ({
        tag: el.tagName,
        cls: String(el.className).slice(0, 60),
        right: Math.round(el.getBoundingClientRect().right),
        width: Math.round(el.getBoundingClientRect().width)
      }))
    })`,
    returnByValue: true,
  });
  console.log(`saved ${outArg} ${width}x${height} dpr=${dpr} theme=${theme}`);
  console.log(metrics.result.value);
  page.close();
} catch (error) {
  console.error("截图失败:", error.message);
  process.exitCode = 1;
} finally {
  child.kill();
  await sleep(300);
  try {
    fs.rmSync(profile, { recursive: true, force: true });
  } catch {
    // 忽略清理失败
  }
}
