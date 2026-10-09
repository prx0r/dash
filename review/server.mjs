// Review dash: Blender jobs + image review + Meshy gate.
// Zero npm deps. node review/server.mjs  (PORT default 8801)
import { createServer } from "node:http";
import { execFile } from "node:child_process";
import { promises as fs } from "node:fs";
import path from "node:path";

const PORT = Number(process.env.PORT || 8801);
const ROOT = new URL("..", import.meta.url).pathname.replace(/\/$/, "");
const DATA = `${ROOT}/review/data`;
const SHOTS = `${ROOT}/review/shots`;
const BLENDER = "/home/ubuntu/blender-5.0.1-linux-x64/blender";
const FREAK = "/home/ubuntu/freaktown";

const JOBS = {
  brick_render: (a) => [BLENDER, ["-b", "--python", `${FREAK}/scripts/render_brick.py`, "--",
    "--glb", a.glb, "--outdir", a.outdir, "--size", String(a.size || 800)]],
  brick_qc: (a) => [BLENDER, ["-b", "--python", `${FREAK}/scripts/brick_qc.py`, "--",
    "--glb", a.glb]],
  brick_repair: (a) => [BLENDER, ["-b", "--python", `${FREAK}/scripts/repair_brick.py`, "--",
    "--glb", a.glb, "--out", a.out, "--height_mm", String(a.height_mm || 75)]],
};

async function ledger() {
  try { return JSON.parse(await fs.readFile(`${DATA}/jobs.json`, "utf8")); }
  catch { return []; }
}
async function saveLedger(j) { await fs.writeFile(`${DATA}/jobs.json`, JSON.stringify(j, null, 1)); }
async function reviews() {
  try { return JSON.parse(await fs.readFile(`${DATA}/reviews.json`, "utf8")); }
  catch { return {}; }
}

function run(cmd, args, log) {
  return new Promise((resolve) => {
    const p = execFile(cmd, args, { timeout: 50 * 60 * 1000, maxBuffer: 64 * 1024 * 1024 },
      (err, stdout, stderr) => resolve({ code: err ? 1 : 0, out: (stdout + stderr).slice(-4000), log }));
    void p;
  });
}

async function handleMcp(message) {
  const { id = null, method, params = {} } = message || {};
  const ok = (result) => ({ jsonrpc: "2.0", id, result });
  const err = (code, message) => ({ jsonrpc: "2.0", id, error: { code, message } });
  try {
    if (method === "initialize") {
      return ok({ protocolVersion: "2026-07-28",
        capabilities: { tools: {} },
        serverInfo: { name: "review-dash", version: "0.1.0" } });
    }
    if (method === "ping") return ok({});
    if (method === "tools/list") {
      return ok({ tools: [
        { name: "list_assets", description: "List review gallery image groups.", inputSchema: { type: "object", properties: {} } },
        { name: "list_models", description: "List 3D models in the 3D room.", inputSchema: { type: "object", properties: {} } },
        { name: "list_jobs", description: "List Blender jobs and statuses.", inputSchema: { type: "object", properties: {} } },
        { name: "submit_job", description: "Submit a Blender job: brick_render, brick_qc, brick_repair.", inputSchema: { type: "object", properties: { kind: { type: "string" }, args: { type: "object" } }, required: ["kind", "args"] } },
        { name: "get_job", description: "Get one job with log tail.", inputSchema: { type: "object", properties: { id: { type: "string" } }, required: ["id"] } },
        { name: "get_reviews", description: "Read human verdicts/notes per asset.", inputSchema: { type: "object", properties: {} } },
        { name: "post_verdict", description: "Leave an approve/redo verdict plus note on an asset (e.g. Hark directing a re-render).", inputSchema: { type: "object", properties: { asset: { type: "string" }, verdict: { type: "string" }, note: { type: "string" } }, required: ["asset", "verdict"] } },
        { name: "blender_docs", description: "Search the local Blender docs mirror + script inventory.", inputSchema: { type: "object", properties: { q: { type: "string" } }, required: ["q"] } },
      ] });
    }
    if (method === "tools/call") {
      const name = params?.name;
      const a = params?.arguments || {};
      if (name === "list_assets") {
        const groups = {};
        for (const f of await fs.readdir(SHOTS).catch(() => [])) {
          const g = f.split("__")[0] || "misc";
          (groups[g] = groups[g] || []).push(`/shots/${f}`);
        }
        return ok({ groups });
      }
      if (name === "list_models") {
        const files = await fs.readdir(`${ROOT}/review/models`).catch(() => []);
        return ok({ models: files.filter((f) => f.endsWith(".glb")) });
      }
      if (name === "list_jobs") return ok({ jobs: await ledger() });
      if (name === "submit_job") {
        if (!JOBS[a.kind]) return err(-32602, "unknown kind");
        const jobs = await ledger();
        const job = { id: `j${Date.now()}`, kind: a.kind, args: a.args || {}, status: "queued", at: new Date().toISOString() };
        jobs.push(job);
        await saveLedger(jobs);
        const [cmd, cargs] = JOBS[job.kind](job.args);
        job.status = "running";
        await saveLedger(jobs);
        run(cmd, cargs).then(async (r) => {
          const all = await ledger();
          const j = all.find((x) => x.id === job.id);
          if (j) { j.status = r.code ? "failed" : "done"; j.result = r.out; await saveLedger(all); }
        });
        return ok({ job });
      }
      if (name === "get_job") {
        const jobs = await ledger();
        const j = jobs.find((x) => x.id === a.id);
        if (!j) return err(-32002, "unknown job");
        return ok({ job: j });
      }
      if (name === "get_reviews") return ok({ reviews: await reviews() });
      if (name === "post_verdict") {
        const rv = await reviews();
        rv[a.asset] = { verdict: a.verdict, note: a.note || "", at: new Date().toISOString(), by: "mcp" };
        await fs.writeFile(`${DATA}/reviews.json`, JSON.stringify(rv, null, 1));
        return ok({ ok: true });
      }
      if (name === "blender_docs") {
        const q = String(a.q || "").toLowerCase();
        const idx = await fs.readFile("/home/ubuntu/blender-docs/INDEX.md", "utf8").catch(() => "");
        return ok({ matches: idx.split("\n").filter((l) => !q || l.toLowerCase().includes(q)).slice(0, 30) });
      }
      return err(-32602, "unknown tool");
    }
    if (method?.startsWith?.("notifications/")) return null;
    return err(-32601, "method not found");
  } catch (e) { return err(-32603, String(e).slice(0, 200)); }
}

const server = createServer(async (req, res) => {
  const u = new URL(req.url, "http://x");
  const send = (code, obj, type = "application/json") => {
    const b = typeof obj === "string" || Buffer.isBuffer(obj) ? obj : JSON.stringify(obj);
    res.writeHead(code, { "content-type": type });
    res.end(b);
  };
  try {
    if (u.pathname === "/" || u.pathname === "/index.html") {
      return send(200, await fs.readFile(`${ROOT}/review/gallery.html`, "utf8"), "text/html; charset=utf-8");
    }
    if (u.pathname === "/3d" || u.pathname === "/three.html") {
      return send(200, await fs.readFile(`${ROOT}/review/three.html`, "utf8"), "text/html; charset=utf-8");
    }
    if (u.pathname === "/api/models") {
      const files = await fs.readdir(`${ROOT}/review/models`).catch(() => []);
      return send(200, files.filter((f) => f.endsWith(".glb")));
    }
    if (u.pathname.startsWith("/models/")) {
      const f = path.normalize(path.join(`${ROOT}/review/models`, u.pathname.slice(8)));
      if (!f.startsWith(`${ROOT}/review/models`)) return send(403, "no");
      return send(200, await fs.readFile(f), "model/gltf-binary");
    }
    if (u.pathname === "/api/docs") {
      const q = (u.searchParams.get("q") || "").toLowerCase();
      const rel = u.searchParams.get("path");
      const DOCS = "/home/ubuntu/blender-docs";
      if (rel) {
        const f = path.normalize(path.join(DOCS, rel));
        if (!f.startsWith(DOCS)) return send(403, "no");
        const t = await fs.readFile(f, "utf8").catch(() => null);
        if (t === null) return send(404, { error: "not found" });
        return send(200, { path: rel, text: t.slice(0, 12000) });
      }
      const idx = await fs.readFile(`${DOCS}/INDEX.md`, "utf8").catch(() => "");
      const lines = idx.split("\n").filter((l) => !q || l.toLowerCase().includes(q));
      return send(200, {
        index_matches: lines.slice(0, 40),
        scripts: [
          "scripts/brick_qc.py (print QC: manifold, bounds, materials)",
          "scripts/repair_brick.py (weld, normals, fill, scale, STL export)",
          "scripts/render_brick.py (turntable + hero stills)",
          "scripts/render_set.py (full performance render)",
          "scripts/puppet_qa.py (evidence bundle)",
        ],
        qc_thresholds: "nonmanifold==0 for print; bounds sane; face visible; holds still in pauses",
      });
    }
    if (u.pathname === "/mcp" && req.method === "POST") {
      const msg = await new Promise((r) => {
        let b = ""; req.on("data", (c) => (b += c)); req.on("end", () => r(b || "{}"));
      }).then((t) => { try { return JSON.parse(t); } catch { return {}; } });
      const r = await handleMcp(msg);
      if (r === null) { res.writeHead(202); return res.end(); }
      return send(200, r);
    }
    if (u.pathname.startsWith("/shots/")) {
      const f = path.normalize(path.join(SHOTS, u.pathname.slice(7)));
      if (!f.startsWith(SHOTS)) return send(403, "no");
      const ext = f.endsWith(".png") ? "image/png" : "image/jpeg";
      return send(200, await fs.readFile(f), ext);
    }
    if (u.pathname === "/api/assets") {
      const groups = {};
      for (const f of await fs.readdir(SHOTS).catch(() => [])) {
        const g = f.split("__")[0] || "misc";
        (groups[g] = groups[g] || []).push(`/shots/${f}`);
      }
      return send(200, { groups, reviews: await reviews() });
    }
    if (u.pathname === "/api/jobs" && req.method === "GET") return send(200, await ledger());
    if (u.pathname === "/api/jobs" && req.method === "POST") {
      const body = JSON.parse(await new Promise((r) => {
        let b = ""; req.on("data", (c) => (b += c)); req.on("end", () => r(b || "{}"));
      }));
      if (!JOBS[body.kind]) return send(400, { error: "unknown kind" });
      const jobs = await ledger();
      const job = { id: `j${Date.now()}`, kind: body.kind, args: body.args || {}, status: "queued", at: new Date().toISOString() };
      jobs.push(job);
      await saveLedger(jobs);
      const [cmd, args] = JOBS[job.kind](job.args);
      job.status = "running";
      await saveLedger(jobs);
      run(cmd, args).then(async (r) => {
        const all = await ledger();
        const j = all.find((x) => x.id === job.id);
        if (j) { j.status = r.code ? "failed" : "done"; j.result = r.out; await saveLedger(all); }
      });
      return send(200, job);
    }
    if (u.pathname === "/api/review" && req.method === "POST") {
      const body = JSON.parse(await new Promise((r) => {
        let b = ""; req.on("data", (c) => (b += c)); req.on("end", () => r(b || "{}"));
      }));
      const rv = await reviews();
      rv[body.asset] = { verdict: body.verdict, note: body.note || "", at: new Date().toISOString() };
      await fs.writeFile(`${DATA}/reviews.json`, JSON.stringify(rv, null, 1));
      return send(200, { ok: true });
    }
    if (u.pathname === "/api/meshy") {
      return send(200, {
        key_present: !!(process.env.MESHY_API_KEY || "").length,
        mode: "dry-run (no spend without explicit approval)",
        note: "Meshy calls cost credits. Submit is disabled until you approve a specific task.",
      });
    }
    return send(404, { error: "not found" });
  } catch (e) { send(500, { error: String(e).slice(0, 200) }); }
});

await fs.mkdir(DATA, { recursive: true });
await fs.mkdir(SHOTS, { recursive: true });
server.listen(PORT, "127.0.0.1", () => console.log(`review dash on ${PORT}`));
