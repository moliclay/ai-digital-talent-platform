import type { Me } from "./api";

/**
 * 与后端 `has_perm` 同口径：`*:action` 视为该动作全模块生效。
 * 不能只用 permissions.includes("sys:view")，admin 下发的是 `*:view`。
 */
export function hasPermission(me: Me | null | undefined, code: string): boolean {
  if (!me) return false;
  const [resource, action] = code.split(":");
  if (!resource || !action) return false;
  return me.permissions.includes(code) || me.permissions.includes(`*:${action}`);
}
