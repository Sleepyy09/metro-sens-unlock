"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const crypto = require("node:crypto");
const html = fs.readFileSync(path.join(__dirname, "..", "MetroSensUnlock.html"), "utf8");
const source = html.match(/<script id="metro-core">([\s\S]*?)<\/script>/)[1];
const Metro = vm.runInNewContext(source + "\nMetro;", {TextEncoder, Uint8Array, DataView});
new vm.Script(html.match(/<script id="metro-ui">([\s\S]*?)<\/script>/)[1]);
let checks = 0;
function test(name, fn) { fn(); checks++; console.log("PASS " + name); }
const copy = bytes => new Uint8Array(bytes);
const names = ["joy_sens_x", ...[0, 1, 2, 3].map(i => `preset${i}_joy_sens_x`), "joy_sens_aiming_x", ...[0, 1, 2, 3].map(i => `preset${i}_joy_sens_aiming_x`)];

// Synthetic PE data only. No copyrighted game bytes are stored or shipped with these tests.
function fixture(base = 0x140000000n, textRva = 0x1000, dataRva = 0x2000) {
    const bytes = new Uint8Array(0x1800), d = new DataView(bytes.buffer);
    const u16 = (o, n) => d.setUint16(o, n, true), u32 = (o, n) => d.setUint32(o, n, true);
    const va = o => base + BigInt(o < 0x800 ? textRva + o - 0x400 : dataRva + o - 0x800);
    u16(0, 0x5a4d); u32(0x3c, 0x80); u32(0x80, 0x4550); u16(0x84, 0x8664); u16(0x86, 2);
    u16(0x94, 240); u16(0x98, 0x20b); d.setBigUint64(0xb0, base, true);
    for (const [i, rva, size, raw, flags] of [[0, textRva, 0x400, 0x400, 0x60000020], [1, dataRva, 0x1000, 0x800, 0x40000040]]) {
        const o = 0x188 + i * 40;
        u32(o + 8, size); u32(o + 12, rva); u32(o + 16, size); u32(o + 20, raw); u32(o + 36, flags);
    }
    names.forEach((name, i) => {
        const e = 0x800 + i * 0x30, s = 0xc00 + i * 64;
        bytes.set(new TextEncoder().encode(name), s);
        d.setBigUint64(e, va(s), true); d.setBigUint64(e + 0x10, va(e + 0x20), true);
        d.setFloat32(e + 0x18, i < 5 ? 0.1 : 0.01, true); d.setFloat32(e + 0x1c, 1, true);
        d.setFloat32(e + 0x20, i < 5 ? 0.95 : 0.7, true);
    });
    function instruction(o, prefix, target) {
        bytes.set(prefix, o);
        d.setInt32(o + prefix.length, Number(va(target) - va(o) - BigInt(prefix.length + 4)), true);
    }
    d.setFloat32(0xb00, 1.5, true); d.setFloat32(0xb04, 0.5, true);
    instruction(0x420, [0xf3, 0x0f, 0x10, 0x15], 0x820);
    instruction(0x440, [0xf3, 0x0f, 0x59, 0x1d], 0xb00);
    instruction(0x460, [0xf3, 0x44, 0x0f, 0x59, 0x15], 0xb04);
    instruction(0x550, [0xf3, 0x44, 0x0f, 0x51, 0x1d], 0x820);
    instruction(0x580, [0xf3, 0x0f, 0x51, 0x05], 0x910);
    return {bytes, d, va, instruction};
}
const stock = fixture().bytes;
test("stock patch validates and changes only planned bytes", () => {
    const original = copy(stock), result = Metro.patch(stock);
    assert.equal(Metro.inspect(stock).state, "stock"); assert.equal(Metro.inspect(result.bytes).state, "patched");
    assert.deepEqual(stock, original); assert.equal(result.bytes.length, stock.length);
    const allowed = new Set();
    Object.entries(result.info.entries).filter(([name]) => names.indexOf(name) < 5).forEach(([, o]) => { for (let i = 0; i < 4; i++) allowed.add(o + 0x1c + i); });
    result.info.patches.forEach(x => { for (let i = 0; i < x.after.length; i++) allowed.add(x.offset + i); });
    let changed = 0;
    stock.forEach((v, i) => { if (v !== result.bytes[i]) { assert.ok(allowed.has(i)); changed++; } });
    assert.equal(result.changed, changed); assert.ok(changed > 0);
});
test("already patched input is unchanged and receives no further patch", () => {
    const patched = Metro.patch(stock).bytes, result = Metro.patch(patched);
    assert.equal(result.changed, 0); assert.deepEqual(result.bytes, patched);
});
test("partial and old max-only patches are refused", () => {
    const old = copy(stock); new DataView(old.buffer).setFloat32(0x81c, 20, true);
    assert.equal(Metro.inspect(old).state, "partial"); assert.throws(() => Metro.patch(old), /Partial patch/);
    const mixed = Metro.patch(stock).bytes; mixed[0x553] = 0x51;
    assert.equal(Metro.inspect(mixed).state, "partial"); assert.throws(() => Metro.patch(mixed), /Partial patch/);
});
test("truncated, overlapping and wrong-architecture PE files are refused", () => {
    for (const length of [0, 255, 256, 0x200, 0x500, 0x1000]) assert.throws(() => Metro.patch(stock.slice(0, length)));
    const x = fixture(); x.d.setUint16(0x84, 0x14c, true); assert.throws(() => Metro.patch(x.bytes), /64-bit/);
    const y = fixture(); y.d.setUint32(0x1b0 + 20, 0x600, true); assert.throws(() => Metro.patch(y.bytes), /Overlapping/);
    const z = fixture(); z.d.setUint32(0x3c, 0xffffffff, true); assert.throws(() => Metro.patch(z.bytes), /invalid/);
});
test("missing and duplicate descriptors are refused", () => {
    const missing = fixture(); missing.bytes[0xc00] = 120; assert.throws(() => Metro.patch(missing.bytes), /descriptors/);
    const duplicate = fixture(); duplicate.bytes.set(duplicate.bytes.slice(0x800, 0x830), 0xa20);
    duplicate.d.setBigUint64(0xa30, duplicate.va(0xa40), true);
    assert.throws(() => Metro.patch(duplicate.bytes), /2 valid descriptors/);
});
test("missing, extra and ambiguous code sites are refused", () => {
    const missing = fixture(); missing.bytes[0x550] = 0; assert.throws(() => Metro.patch(missing.bytes), /legacy/);
    const extra = fixture(); extra.instruction(0x600, [0xf3, 0x44, 0x0f, 0x51, 0x1d], 0x820); assert.throws(() => Metro.patch(extra.bytes), /legacy/);
    const ambiguous = fixture(); ambiguous.instruction(0x480, [0xf3, 0x0f, 0x59, 0x1d], 0xb00); assert.throws(() => Metro.patch(ambiguous.bytes), /ambiguous/);
    const anchor = fixture(); anchor.instruction(0x620, [0xf3, 0x0f, 0x10, 0x15], 0x820); assert.throws(() => Metro.patch(anchor.bytes), /look function/);
});
test("exact 64-bit pointers and negative RIP displacements work", () => {
    for (const f of [fixture(0x1000000140000000n), fixture(0x140000000n, 0x8000, 0x1000)]) assert.equal(Metro.inspect(Metro.patch(f.bytes).bytes).state, "patched");
});
const cfgText = "gamepad_preset 1\r\n_gamepad_preset_sens 2\r\njoy_sens_x 0.5\r\njoy_sens_aiming_x 0.45\r\npreset0_joy_sens_x 0.81999999\r\nr_gamma 1.2\r\n";
const encode = s => new TextEncoder().encode(s);
test("config changes active sensitivities and preserves unrelated UTF-8 bytes", () => {
    const input = encode("\ufeff" + cfgText + "nickname José\r\n"), original = copy(input), result = Metro.config(input, 2.5, 0.6);
    const expected = "\ufeff" + cfgText.replace("joy_sens_x 0.5", "joy_sens_x 2.5").replace("joy_sens_aiming_x 0.45", "joy_sens_aiming_x 0.6") + "nickname José\r\npreset1_joy_sens_x 2.5\r\npreset1_joy_sens_aiming_x 0.6\r\npreset2_joy_sens_x 2.5\r\npreset2_joy_sens_aiming_x 0.6\r\n";
    assert.deepEqual(result.bytes, encode(expected)); assert.deepEqual(input, original);
});
test("config preserves existing spacing, LF and ANSI bytes", () => {
    const input = Uint8Array.from(Buffer.from("joy_sens_x\t0.5  \njoy_sens_aiming_x 0.7\nlabel \xe9", "latin1"));
    const result = Metro.config(input, 1.3, 1).bytes;
    assert.ok(Buffer.from(result).includes(Buffer.from("joy_sens_x\t1.3  \njoy_sens_aiming_x 1\nlabel \xe9\n", "latin1")));
    assert.equal(result.includes(13), false);
});
test("config rejects duplicates, invalid numbers, invalid presets and wrong files", () => {
    for (const bad of [cfgText + "joy_sens_x 1\n", cfgText.replace("0.5\r", "NaN\r"), cfgText.replace("0.5\r", "Infinity\r"), cfgText.replace("preset 1", "preset 4"), "hello", "\0\0", cfgText.replace("0.5\r", "1x\r")]) assert.throws(() => Metro.config(encode(bad), 2, 0.7));
    for (const [look, ads] of [[NaN, .5], [2, Infinity], [.09, .5], [21, .5], [1, .04], [1, 1.01]]) assert.throws(() => Metro.config(encode(cfgText), look, ads));
});
test("initial values reflect stock preset conversion or existing patched settings", () => {
    assert.equal(Metro.initialSettings(encode(cfgText), "stock").look, 0.7071);
    assert.equal(Metro.initialSettings(encode(cfgText.replace("sens 2", "sens 3")), "stock").look, 0.9444);
    assert.equal(Metro.initialSettings(encode(cfgText.replace("joy_sens_x 0.5", "joy_sens_x 7.5")), "patched").look, 7.5);
});
test("HTML has no external assets, network calls or executable dependencies", () => {
    assert.match(html, /connect-src 'none'/); assert.match(html, /form-action 'none'/);
    assert.doesNotMatch(html, /<(?:script|img|iframe)\b[^>]*\bsrc\s*=/i);
    assert.doesNotMatch(html, /\b(?:fetch|XMLHttpRequest|WebSocket|EventSource|sendBeacon|eval|localStorage|sessionStorage|serviceWorker)\s*(?:\(|\.|=)/);
    assert.doesNotMatch(html, /https?:\/\//);
});
function luminance(hex) {
    const rgb = hex.match(/\w\w/g).map(v => parseInt(v, 16) / 255).map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4);
    return rgb[0] * .2126 + rgb[1] * .7152 + rgb[2] * .0722;
}
test("text and control colours meet WCAG AA contrast", () => {
    for (const block of [...html.matchAll(/:root\{([^}]+)\}/g)].map(m => m[1])) {
        const palette = Object.fromEntries([...block.matchAll(/--([\w-]+):#([0-9a-f]+)\b/g)].map(m => [m[1], m[2].length === 3 ? [...m[2]].map(c => c + c).join("") : m[2]]));
        const ratio = (a, b) => { const x = luminance(palette[a]), y = luminance(palette[b]); return (Math.max(x, y) + .05) / (Math.min(x, y) + .05); };
        for (const c of ["text", "muted", "accent", "error"]) for (const bg of ["background", "panel"]) assert.ok(ratio(c, bg) >= 4.5, `${c}/${bg}: ${ratio(c, bg)}`);
        assert.ok(ratio("on-accent", "accent") >= 4.5);
        assert.ok(ratio("line", "panel") >= 3);
    }
});
if (process.argv.length > 2) {
    assert.equal(process.argv.length, 4, "Pass a stock backup path and patched executable path together.");
    test("local game parity, read-only", () => {
        const original = copy(fs.readFileSync(process.argv[2])), expected = copy(fs.readFileSync(process.argv[3]));
        assert.equal(Metro.inspect(original).state, "stock"); assert.equal(Metro.inspect(expected).state, "patched");
        const actual = Metro.patch(original);
        assert.deepEqual(actual.bytes, expected);
        console.log(`Local parity: ${actual.changed} changed bytes; SHA-256 ${crypto.createHash("sha256").update(actual.bytes).digest("hex")}`);
    });
}
// A small DOM substitute checks our event logic. It does not claim browser rendering or downloads work.
async function uiChecks() {
    const elements = new Map(), blobs = new Map();
    let nextUrl = 0;
    class Element {
        constructor(id) { this.id = id; this.value = ""; this.files = []; this.checked = false; this.disabled = false; this.hidden = false; this.textContent = ""; this.listeners = {}; this.classList = {toggle() {}}; }
        get valueAsNumber() { return this.value === "" ? NaN : Number(this.value); }
        get validity() { return {valid: Number.isFinite(this.valueAsNumber)}; }
        addEventListener(event, fn) { this.listeners[event] = fn; }
        removeAttribute(name) { delete this[name]; }
        async fire(event) { return this.listeners[event]?.({target: this}); }
    }
    const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(m => m[1]);
    ids.forEach(id => elements.set(id, new Element(id)));
    const get = id => elements.get(id);
    const context = {TextEncoder, Uint8Array, DataView, Blob, crypto: {subtle: {digest: (...args) => crypto.webcrypto.subtle.digest(...args)}}, document: {getElementById: get}, URL: {
        createObjectURL(blob) { const url = "blob:test/" + ++nextUrl; blobs.set(url, blob); return url; },
        revokeObjectURL(url) { blobs.delete(url); }
    }};
    vm.runInNewContext(source + "\n" + html.match(/<script id="metro-ui">([\s\S]*?)<\/script>/)[1], context);
    async function select(kind, bytes) {
        get(kind + "-file").files = [{size: bytes.length, arrayBuffer: async () => bytes.slice().buffer}];
        await get(kind + "-file").fire("change");
    }
    async function confirm() { get("backup-check").checked = true; await get("backup-check").fire("change"); }
    await select("exe", stock); await select("cfg", encode(cfgText));
    assert.equal(get("prepare").disabled, true);
    await confirm(); assert.equal(get("prepare").disabled, false);
    get("look").value = "2.5"; get("ads").value = "60";
    await get("prepare").fire("click");
    assert.equal(get("results").hidden, false); assert.equal(blobs.size, 2);
    const exeBlob = blobs.get(get("exe-download").href), cfgBlob = blobs.get(get("cfg-download").href);
    assert.deepEqual(new Uint8Array(await exeBlob.arrayBuffer()), Metro.patch(stock).bytes);
    assert.deepEqual(new Uint8Array(await cfgBlob.arrayBuffer()), Metro.config(encode(cfgText), 2.5, .6).bytes);
    assert.equal(get("exe-download").download, "MetroExodus.exe"); assert.equal(get("cfg-download").download, "user.cfg");
    test("UI prepares exact copies only after confirmation", () => {});
    get("look").value = "3"; await get("look").fire("input");
    assert.equal(get("results").hidden, true); assert.equal(blobs.size, 0); assert.equal(get("exe-download").href, undefined);
    get("look").value = ""; await get("prepare").fire("click");
    assert.equal(blobs.size, 0); assert.match(get("result-status").textContent, /Look speed must/);
    get("look-range").value = "2"; await get("look-range").fire("input"); assert.equal(get("look").value, "2");
    await get("prepare").fire("click"); await get("backup-check").fire("change"); assert.equal(blobs.size, 0);
    test("UI invalidates stale links and rejects invalid numeric input", () => {});
    await select("exe", Metro.patch(stock).bytes); await confirm(); await get("prepare").fire("click");
    assert.equal(blobs.size, 1); assert.equal(get("exe-download").hidden, true);
    const mixed = copy(stock); new DataView(mixed.buffer).setFloat32(0x81c, 20, true);
    await select("exe", mixed); assert.equal(blobs.size, 0); assert.equal(get("prepare").disabled, true);
    await select("exe", encode("not an exe")); assert.equal(get("prepare").disabled, true);
    test("UI accepts patched inputs for config only and refuses partial/bad files", () => {});
    let finishOld;
    get("exe-file").files = [{size: stock.length, arrayBuffer: () => new Promise(resolve => { finishOld = resolve; })}];
    const oldSelection = get("exe-file").fire("change");
    await select("exe", Metro.patch(stock).bytes); finishOld(stock.slice().buffer); await oldSelection;
    assert.match(get("exe-status").textContent, /Already patched/);
    await confirm();
    const digest = context.crypto.subtle.digest;
    let finishHash;
    context.crypto.subtle.digest = () => new Promise(resolve => { finishHash = resolve; });
    const preparing = get("prepare").fire("click");
    get("look").value = "4"; await get("look").fire("input");
    finishHash(new ArrayBuffer(32)); await preparing;
    assert.equal(blobs.size, 0); assert.equal(get("results").hidden, true);
    context.crypto.subtle.digest = digest;
    test("UI ignores stale asynchronous file reads and preparation results", () => {});
}
uiChecks().then(() => console.log(`${checks} checks passed.`)).catch(error => { console.error(error); process.exitCode = 1; });
