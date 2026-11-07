#!/usr/bin/env node
/* 验收 IIFE 产物：语法、导出完整性、OrbitControls、无残留 ESM 语法、无外网依赖。
 * 用法：node build/verify_bundle.mjs   （失败时退出码非 0）
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const src = fs.readFileSync(path.join(root, 'vendor/three.module.js'), 'utf8');
const bundle = fs.readFileSync(path.join(root, 'vendor/three.iife.js'), 'utf8');

// 1) 抽取源文件 export 名单
const m = /\bexport\s*\{([\s\S]*?)\}\s*;?\s*$/.exec(src.trim());
if (!m) throw new Error('源文件末尾 export 列表未找到');
const names = m[1].split(',').map(s => s.trim()).filter(Boolean)
  .map(s => (s.includes(' as ') ? s.split(/\s+as\s+/)[1].trim() : s));
console.log('源文件导出名：' + names.length + ' 个');

// 2) 在 Node 沙箱里执行 IIFE，取回全局 THREE
const sandbox = { window: {}, document: undefined, self: undefined, console };
const keys = Object.keys(sandbox);
const fn = new Function(...keys, bundle + '\nreturn (typeof THREE!=="undefined" ? THREE : window.THREE);');
const THREE = fn(...keys.map(k => sandbox[k]));
if (!THREE || typeof THREE !== 'object') throw new Error('IIFE 未产生全局 THREE 对象');

const missing = names.filter(n => !(n in THREE));
if (missing.length) throw new Error('导出缺失：' + missing.join(', '));
if (typeof THREE.WebGLRenderer !== 'function') throw new Error('WebGLRenderer 不是构造函数');
if (typeof THREE.OrbitControls !== 'function') throw new Error('OrbitControls 未挂载');
if (THREE.REVISION !== '160') throw new Error('REVISION 异常：' + THREE.REVISION);
console.log('全局 THREE 导出完整：' + Object.keys(THREE).length + ' 个键，含 OrbitControls，r' + THREE.REVISION);

// 3) 语法与 ESM 残留检查（普通脚本不得含 import/export 语句）
if (/^\s*(import|export)\s/m.test(bundle)) throw new Error('产物中残留 ESM import/export 语句');
if (bundle.includes('import.meta')) throw new Error('产物中残留 import.meta');
if (/(?:src|href)\s*=\s*["']https?:\/\//.test(bundle)) throw new Error('产物含外链');
console.log('结构检查 OK：无 ESM 语法、无 import.meta、无外链');

// 4) 关键类可用性与最小实例化（不接触 WebGL 上下文）
const v = new THREE.Vector3(1, 2, 3);
if (v.lengthSq() !== 14) throw new Error('Vector3 运算异常');
const c = new THREE.Color(0xA9A29B);
if (!/^[0-9a-f]{6}$/.test(c.getHexString())) throw new Error('Color 运算异常');
console.log('冒烟测试 OK：Vector3 / Color 可用');
console.log('\nIIFE 打包验收通过。');
