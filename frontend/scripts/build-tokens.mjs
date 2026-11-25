#!/usr/bin/env node
/**
 * 从 tokens.json 生成 src/styles/tokens.css。
 * 规则：
 * 1. 只输出 semantic 与 component 两层；primitive 只在解析别名时使用。
 * 2. component 里指向 semantic 的别名输出为 var(--x)，不冻结成 hex，保证主题切换生效。
 * 3. dark 段只覆盖同名语义变量，写在 :root[data-theme="dark"] 里。
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const source = path.join(root, "tokens.json");
const target = path.join(root, "src", "styles", "tokens.css");

const tokens = JSON.parse(fs.readFileSync(source, "utf8"));

function flatten(node, prefix = "", out = {}) {
  if (!node || typeof node !== "object") return out;
  if ("$value" in node) {
    out[prefix] = { value: node.$value, type: node.$type };
    return out;
  }
  for (const [key, value] of Object.entries(node)) {
    if (key.startsWith("$")) continue;
    flatten(value, prefix ? `${prefix}.${key}` : key, out);
  }
  return out;
}

const nodes = flatten(tokens);

function resolve(ref) {
  let current = nodes[ref];
  let guard = 0;
  while (current && typeof current.value === "string" && /^\{.+\}$/.test(current.value) && guard < 12) {
    const next = current.value.slice(1, -1).trim();
    current = nodes[next];
    guard += 1;
  }
  return current ? current.value : undefined;
}

function cssValue(value, type) {
  if (Array.isArray(value)) {
    if (type === "cubicBezier") return `cubic-bezier(${value.join(", ")})`;
    if (type === "fontFamily") {
      return value.map((name) => (/\s/.test(name) ? `"${name}"` : name)).join(", ");
    }
    return value.join(", ");
  }
  if (typeof value === "number") return String(value);
  return String(value);
}

function varName(tokenPath) {
  if (tokenPath.startsWith("light.")) return varName(tokenPath.slice("light.".length));
  const parts = tokenPath.split(".");
  if (parts[0] === "semantic") {
    const group = parts[1];
    const rest = parts.slice(2);
    if (group === "type") {
      const kind = rest[0];
      const tail = rest.slice(1).join("-");
      if (kind === "size") return `--font-${tail}`;
      if (kind === "family") return `--font-family-${tail}`;
      if (kind === "weight") return `--weight-${tail}`;
      if (kind === "leading") return `--leading-${tail}`;
      if (kind === "tracking") return `--tracking-${tail}`;
    }
    if (group === "motion" && rest[0] === "duration") return `--motion-${rest.slice(1).join("-")}`;
    if (group === "motion" && rest[0] === "easing") return `--ease-${rest.slice(1).join("-")}`;
    if (group === "borderWidth") return `--border-width-${rest.join("-")}`;
    if (group === "space") return `--space-${rest.join("-")}`;
    if (group === "radius") return `--radius-${rest.join("-")}`;
    if (group === "shadow") return `--shadow-${rest.join("-")}`;
    if (group === "layout") return `--layout-${rest.join("-")}`;
    if (group === "z") return `--z-${rest.join("-")}`;
    if (group === "breakpoint") return `--bp-${rest.join("-")}`;
    return `--${group}-${rest.join("-")}`;
  }
  if (parts[0] === "component") return `--${parts.slice(1).join("-")}`;
  return null;
}

function line(tokenPath, node) {
  const name = varName(tokenPath);
  if (!name) return "";
  const raw = node.value;
  const isAlias = typeof raw === "string" && /^\{.+\}$/.test(raw);
  const ref = isAlias ? raw.slice(1, -1).trim() : "";
  let value;
  if (isAlias && tokenPath.startsWith("component.") && ref.startsWith("semantic.")) {
    value = `var(${varName(ref)})`;
  } else {
    const resolved = isAlias ? resolve(ref) : raw;
    if (resolved === undefined) return `  /* MISSING ${tokenPath} -> ${raw} */`;
    value = cssValue(resolved, node.type);
  }
  const ctIgnore =
    tokenPath.startsWith("semantic.enterprise")
      ? " /* taste-skill-ignore: Corporate Trust 设计规范要求品牌渐变与彩色阴影 */"
      : tokenPath.startsWith("semantic.glass") || tokenPath.startsWith("light.semantic.glass")
        ? " /* taste-skill-ignore: Glass 设计规范要求分层玻璃与光斑 */"
        : "";
  const brandColorIgnore = /#4f46e5|#7c3aed/i.test(String(value))
    ? " /* taste-skill-ignore: Corporate Trust 品牌主色 */"
    : "";
  return `  ${name}: ${value};${name === "--font-family-mono" ? " /* taste-skill-ignore: 等宽只用于 ID 与代码 */" : ""}${ctIgnore}${brandColorIgnore}`;
}

const rootLines = [];
const darkLines = [];
const lightLines = [];

for (const [tokenPath, node] of Object.entries(nodes)) {
  if (tokenPath.startsWith("light.")) {
    if (node.type === "string") continue;
    const out = line(tokenPath, node);
    if (out) lightLines.push(out);
    continue;
  }
  if (!tokenPath.startsWith("semantic.") && !tokenPath.startsWith("component.")) continue;
  if (node.type === "string") continue;
  const out = line(tokenPath, node);
  if (out) rootLines.push(out);

  if (tokenPath.startsWith("semantic.")) {
    const darkPath = `dark.${tokenPath.slice("semantic.".length)}`;
    const darkNode = nodes[darkPath];
    if (darkNode) {
      const raw = darkNode.value;
      const resolved =
        typeof raw === "string" && /^\{.+\}$/.test(raw) ? resolve(raw.slice(1, -1).trim()) : raw;
      if (resolved !== undefined && darkNode.type !== "string") {
        darkLines.push(`  ${varName(tokenPath)}: ${cssValue(resolved, darkNode.type)};`);
      }
    }
  }
}

const header = `/* 由 scripts/build-tokens.mjs 从 tokens.json 生成，不要手改。 */\n\n:root {\n  color-scheme: light;\n`;

const darkHeader = `\n:root[data-theme="dark"] {\n  color-scheme: dark;\n`;
const lightHeader = `\n:root[data-theme="light"] {\n  color-scheme: light;\n`;

const css = `${header}${rootLines.join("\n")}\n}\n${darkHeader}${darkLines.join("\n")}\n}\n${lightHeader}${lightLines.join("\n")}\n}\n`;

fs.mkdirSync(path.dirname(target), { recursive: true });
fs.writeFileSync(target, css, "utf8");
console.log(`tokens.css: ${rootLines.length} variables, ${darkLines.length} dark overrides, ${lightLines.length} light overrides`);
