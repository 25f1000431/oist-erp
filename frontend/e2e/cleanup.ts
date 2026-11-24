import { rmSync } from "node:fs";

export default async function globalTeardown() {
  for (const path of [process.env.E2E_SQLITE_FILE, process.env.E2E_RESULTS_DIR]) {
    if (path) rmSync(path, { force: true, recursive: true });
  }
}
