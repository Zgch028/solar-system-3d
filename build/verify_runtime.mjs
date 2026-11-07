#!/usr/bin/env node
/* 3D 层「WebGL 可用」路径初始化冒烟测试 —— 零依赖，Node 18+ 可跑。
 *
 * 背景（2026-11-07 手机微信真机反馈）：verify_compat.py 第 6 项只模拟
 * 「WebGL 被禁用」，3D 层在探测处就提前 return，从未执行到
 * `new OrbitControls(...)`。因此一个裸标识符引用错误（IIFE 把控制器挂在
 * window.THREE.OrbitControls，页面却写 new OrbitControls）溜过了全部 8 项
 * 本机验收，直到真机打开才暴露为「3D 初始化异常：Can't find variable:
 * OrbitControls」并掉进静态降级视图。
 *
 * 本脚本补上被漏掉的路径：让 WebGL 探测通过，加载**真实的**
 * vendor/three.iife.js（415 个真类 + OrbitControls），只把需要 GPU/DOM 的
 * WebGLRenderer 与 OrbitControls 换成可计数 stub，然后端到端执行数值层、
 * 降级层、3D 层三个脚本块，断言 3D 层完整启动、没有触发降级、且
 * OrbitControls 构造确实被调用了一次。
 *
 * 关键性质：3D 层若再写裸 `OrbitControls`，new Function 作用域里没有该
 * 变量，会抛 ReferenceError 被 catch 捕获并降级 —— 本测试立即失败。
 * 这比静态文本匹配更强，因为它验证的是真实执行路径。
 *
 * 用法：node build/verify_runtime.mjs [--root <作品目录>]
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
let ROOT = path.resolve(HERE, '..');
const ri = process.argv.indexOf('--root');
if (ri > -1) ROOT = path.resolve(process.argv[ri + 1]);

const MAIN = path.join(ROOT, '太阳系八大行星动态运转.html');
const BUNDLE = path.join(ROOT, 'vendor/three.iife.js');
const html = fs.readFileSync(MAIN, 'utf8');
const bundle = fs.readFileSync(BUNDLE, 'utf8');

const blocks = [...html.matchAll(/<script>\n([\s\S]*?)\n<\/script>/g)].map(m => m[1]);
function pick(kw) {
  const a = blocks.filter(b => b.includes(kw));
  if (a.length !== 1) throw new Error('脚本块定位失败：' + kw + '（命中 ' + a.length + ' 个）');
  return a[0];
}
const numeric = pick('window.SOLAR = Object.freeze(');
const fallbackLayer = pick('window.__SOLAR_FALLBACK__=render');
const layer3d = pick('3D-LAYER-BEGIN');

// ---- DOM / BOM stub：只实现 3D 层初始化实际会碰到的接口 -------------------
const calls = { renderer: 0, controls: 0, raf: 0 };
const ctx2d = {
  fillStyle: '', fillRect() {}, beginPath() {}, arc() {}, fill() {},
  createLinearGradient() { return { addColorStop() {} }; }
};
const nodes = new Map();
function makeNode(id) {
  const n = {
    id, tagName: 'DIV', innerHTML: '', textContent: '', value: '', className: '',
    width: 0, height: 0, style: {}, dataset: {},
    classList: { add() {}, remove() {}, toggle() {} },
    appendChild() {}, removeChild() {}, setAttribute() {}, removeAttribute() {},
    addEventListener() {}, removeEventListener() {},
    getContext() { return ctx2d; },
    getBoundingClientRect() { return { left: 0, top: 0, width: 800, height: 600 }; },
    getRootNode() { return documentStub; },
    ownerDocument: null
  };
  return n;
}
const documentStub = {
  getElementById(id) {
    if (!nodes.has(id)) nodes.set(id, makeNode(id));
    return nodes.get(id);
  },
  createElement(tag) { const n = makeNode('#' + tag); n.tagName = tag.toUpperCase(); return n; },
  body: { classList: { add() {}, remove() {} }, style: {} },
  activeElement: { tagName: 'BODY' },
  addEventListener() {}, removeEventListener() {}
};
const windowStub = {
  innerWidth: 800, innerHeight: 600, devicePixelRatio: 1,
  // 关键：探测结果为「WebGL 可用」，3D 层不得在探测处提前返回
  __WEBGL__: { ok: true, reason: 'verify_runtime：WebGL 可用', renderer: 'stub-webgl2' },
  __bootTimer: null,
  addEventListener() {}, removeEventListener() {},
  matchMedia() { return { matches: false }; },
  requestAnimationFrame() { calls.raf++; return 1; },  // 只登记，不执行帧循环
  cancelAnimationFrame() {},
  setTimeout, clearTimeout, performance
};
globalThis.window = windowStub;
globalThis.document = documentStub;
globalThis.self = windowStub;
globalThis.requestAnimationFrame = windowStub.requestAnimationFrame;
globalThis.cancelAnimationFrame = () => {};
if (typeof globalThis.navigator === 'undefined') {
  try { globalThis.navigator = { userAgent: 'node-verify-runtime' }; } catch (_) { /* 只读则跳过 */ }
}

// ---- 加载真实 IIFE 包，再替换两处需要 GPU / DOM 事件的类 -------------------
const realLog = console.log, realErr = console.error, realWarn = console.warn;
const errLogs = [];
console.log = () => {};
console.warn = () => {};
console.error = (...a) => { errLogs.push(a.map(String).join(' ')); };
try {
  new Function(bundle)();
  const THREE = window.THREE;
  if (!THREE || typeof THREE.Scene !== 'function') {
    throw new Error('three.iife.js 未正确挂载 window.THREE');
  }
  if (typeof THREE.OrbitControls !== 'function') {
    throw new Error('three.iife.js 未挂载 window.THREE.OrbitControls');
  }

  class WebGLRendererStub {
    constructor(opts) {
      calls.renderer++;
      this.domElement = opts && opts.canvas;
      this.outputColorSpace = '';
    }
    setPixelRatio() {} setSize() {} render() {}
  }
  class OrbitControlsStub {
    constructor(camera, dom) {
      calls.controls++;
      this.domElement = dom;
      this.target = new THREE.Vector3();
      this.enableDamping = false;
    }
    update() {}
  }
  // 保留其余 415 个真实 Three.js 类（几何体、材质、Color、Vector3…）
  THREE.WebGLRenderer = WebGLRendererStub;
  THREE.OrbitControls = OrbitControlsStub;

  for (const code of [numeric, fallbackLayer, layer3d]) new Function(code)();
} catch (e) {
  console.log = realLog; console.warn = realWarn; console.error = realErr;
  console.error('3D 初始化冒烟验收：执行期抛出异常 —— ' + (e && e.stack ? e.stack : String(e)));
  process.exit(1);
}
console.log = realLog; console.warn = realWarn; console.error = realErr;

// ---- 断言：3D 层必须完整启动，且没有掉进降级视图 ---------------------------
const problems = [];
if (calls.renderer !== 1) problems.push('WebGLRenderer 构造次数 = ' + calls.renderer + '（应为 1）');
if (calls.controls !== 1) problems.push('OrbitControls 构造次数 = ' + calls.controls + '（应为 1）');
if (window.__FALLBACK__ === true) {
  problems.push('3D 层意外触发降级视图：' + (nodes.get('fb-reason') || {}).textContent);
}
if (window.__BOOTED !== true) problems.push('未标记 window.__BOOTED');
if (!window.__MODE3D__) problems.push('未标记 window.__MODE3D__（启动段未跑完）');
const loaderrNode = nodes.get('loaderr');
if (!loaderrNode || loaderrNode.style.display !== 'none') problems.push('加载错误提示未隐藏');
const fallbackNode = nodes.get('fallback');   // 未降级时 render() 不执行，此节点可能从未被创建
if (fallbackNode && fallbackNode.style.display === 'block') problems.push('降级视图被显示');
if (errLogs.length) problems.push('控制台报错：' + errLogs.join(' | '));

if (problems.length) {
  for (const p of problems) console.error('  FAIL ' + p);
  console.error('3D 初始化冒烟验收：失败');
  process.exit(1);
}
console.log('  WebGL 可用路径：3D 层完整启动，WebGLRenderer / OrbitControls 各构造 1 次，帧循环已登记 %d 次', calls.raf);
console.log('  降级视图未触发；__BOOTED=%s；__MODE3D__=%s', window.__BOOTED, window.__MODE3D__);
console.log('3D 初始化冒烟验收通过：真实 THREE 符号引用完整，手机端不会再因裸标识符掉降级。');
