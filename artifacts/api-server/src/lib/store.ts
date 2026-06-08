import { readFileSync, writeFileSync, existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = join(__dirname, "../../data");
import { mkdirSync } from "fs";
try { mkdirSync(DATA_DIR, { recursive: true }); } catch {}

function filePath(name: string) {
  return join(DATA_DIR, `${name}.json`);
}

function readJson<T>(name: string, defaultVal: T): T {
  const p = filePath(name);
  if (!existsSync(p)) return defaultVal;
  try { return JSON.parse(readFileSync(p, "utf-8")) as T; } catch { return defaultVal; }
}

function writeJson(name: string, data: unknown) {
  writeFileSync(filePath(name), JSON.stringify(data), "utf-8");
}

export function getExecuteCount(): number {
  return readJson<number>("executeCount", 31957);
}

export function incrementExecuteCount(): number {
  const c = getExecuteCount() + 1;
  writeJson("executeCount", c);
  return c;
}

export interface ApiEntry {
  apiId: string;
  apiName: string;
  webhook: string;
  rateLimit: number;
}

export function getApiRegistry(): Record<string, ApiEntry> {
  return readJson<Record<string, ApiEntry>>("apiRegistry", {});
}

export function saveApiEntry(entry: ApiEntry) {
  const reg = getApiRegistry();
  reg[entry.apiId] = entry;
  writeJson("apiRegistry", reg);
}

export function getApiEntry(apiId: string): ApiEntry | undefined {
  return getApiRegistry()[apiId];
}
