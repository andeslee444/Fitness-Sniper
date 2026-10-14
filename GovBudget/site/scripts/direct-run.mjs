/**
 * direct-run.mjs — "is this module the script node was asked to run?"
 *
 * ROADMAP #201: five scripts compared process.argv[1] with their own path as
 * strings. Node resolves the main module's symlinks (import.meta.url is the
 * real path) but leaves argv[1] as typed, so a script run through a
 * symlinked spelling — a worktree link, /tmp for /private/tmp — saw two
 * different strings, skipped its body and exited 0 having checked nothing.
 * Compare real paths instead.
 */
import fs from "fs";
import { fileURLToPath } from "url";

/** True when `argv1` (default process.argv[1]) is the file `moduleUrl` names. */
export function isDirectRun(moduleUrl, argv1 = process.argv[1]) {
  if (!argv1) return false;
  try {
    return fs.realpathSync(argv1) === fs.realpathSync(fileURLToPath(moduleUrl));
  } catch {
    return false;
  }
}
