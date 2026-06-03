#!/usr/bin/env node
/**
 * claude-release-radar CLI installer.
 *
 * Usage:
 *   npx claude-release-radar install        Copy the skill into ~/.claude/skills/
 *   npx claude-release-radar install --dir <path>
 *   npx claude-release-radar check [...]     Run the Python engine (passes args through)
 *   npx claude-release-radar where           Print the packaged skill path
 *
 * Pure Node, no dependencies.
 */
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const PKG_ROOT = path.resolve(__dirname, "..");
const SKILL_NAME = "claude-release-radar";
const SKILL_FILES = ["SKILL.md", "scripts", "reference"]; // what a skill needs at runtime

// Don't crash if our output is piped into something that closes early (e.g. `| head`).
process.stdout.on("error", (e) => { if (e.code === "EPIPE") process.exit(0); });

function log(msg) { process.stdout.write(msg + "\n"); }
function fail(msg) { process.stderr.write("✖ " + msg + "\n"); process.exit(1); }

function copyRecursive(src, dest) {
  const stat = fs.statSync(src);
  if (stat.isDirectory()) {
    fs.mkdirSync(dest, { recursive: true });
    for (const entry of fs.readdirSync(src)) {
      copyRecursive(path.join(src, entry), path.join(dest, entry));
    }
  } else {
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.copyFileSync(src, dest);
  }
}

function pythonBin() {
  for (const c of ["python3", "python"]) {
    const r = spawnSync(c, ["--version"], { stdio: "ignore" });
    if (r.status === 0) return c;
  }
  return null;
}

function install(args) {
  const dirFlag = args.indexOf("--dir");
  const targetRoot = dirFlag !== -1 && args[dirFlag + 1]
    ? path.resolve(args[dirFlag + 1])
    : path.join(os.homedir(), ".claude", "skills");
  const dest = path.join(targetRoot, SKILL_NAME);

  fs.mkdirSync(targetRoot, { recursive: true });
  for (const f of SKILL_FILES) {
    const src = path.join(PKG_ROOT, f);
    if (fs.existsSync(src)) copyRecursive(src, path.join(dest, f));
  }
  log(`✔ Installed ${SKILL_NAME} → ${dest}`);
  log(`  Now ask Claude: "what's new in Claude?"`);
}

function check(args) {
  const py = pythonBin();
  if (!py) fail("Python 3 not found on PATH. Install Python 3.8+ and retry.");
  const engine = path.join(PKG_ROOT, "scripts", "radar.py");
  const r = spawnSync(py, [engine, "check", ...args], { stdio: "inherit" });
  process.exit(r.status === null ? 1 : r.status);
}

function main() {
  const [cmd, ...rest] = process.argv.slice(2);
  switch (cmd) {
    case "install": return install(rest);
    case "check": return check(rest);
    case "where": return log(PKG_ROOT);
    case undefined:
    case "help":
    case "--help":
    case "-h":
      log("claude-release-radar — keep current on Claude releases\n");
      log("Commands:");
      log("  install [--dir <path>]   Copy the skill into ~/.claude/skills/");
      log("  check [...args]          Run the engine (forwards args to radar.py)");
      log("  where                    Print the packaged skill path");
      return;
    default:
      fail(`Unknown command: ${cmd}. Try 'install', 'check', or 'help'.`);
  }
}

main();
