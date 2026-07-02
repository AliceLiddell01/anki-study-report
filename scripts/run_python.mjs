import { existsSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

const args = process.argv.slice(2);

if (!args.length) {
  console.error("Usage: node scripts/run_python.mjs <python args...>");
  process.exit(2);
}

const candidates = [];

if (process.env.PYTHON) {
  candidates.push([process.env.PYTHON]);
}

const bundledPython = process.env.USERPROFILE
  ? join(
      process.env.USERPROFILE,
      ".cache",
      "codex-runtimes",
      "codex-primary-runtime",
      "dependencies",
      "python",
      "python.exe",
    )
  : "";
if (bundledPython && existsSync(bundledPython)) {
  candidates.push([bundledPython]);
}

candidates.push(["python"], ["python3"]);
if (process.platform === "win32") {
  candidates.push(["py", "-3"]);
}

const python = findPython(candidates);
if (!python) {
  console.error("Could not find a working Python interpreter. Set PYTHON to its full path.");
  process.exit(1);
}

const result = spawnSync(python[0], [...python.slice(1), ...args], {
  cwd: process.cwd(),
  env: process.env,
  shell: false,
  stdio: "inherit",
});

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}
process.exit(result.status ?? 1);

function findPython(options) {
  for (const command of options) {
    const probe = spawnSync(command[0], [...command.slice(1), "--version"], {
      shell: false,
      stdio: "pipe",
      encoding: "utf8",
    });
    if (probe.status === 0 && `${probe.stdout}${probe.stderr}`.includes("Python")) {
      return command;
    }
  }
  return null;
}
