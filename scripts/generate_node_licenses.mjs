import { readFile, writeFile } from "node:fs/promises";

const lock = JSON.parse(await readFile(new URL("../web/package-lock.json", import.meta.url), "utf8"));
const rows = Object.entries(lock.packages)
  .filter(([path, metadata]) => path.startsWith("node_modules/") && !metadata.dev)
  .map(([path, metadata]) => ({
    name: path.replace(/^node_modules\//, ""),
    version: metadata.version ?? "unknown",
    license: metadata.license ?? "UNKNOWN",
  }))
  .sort((left, right) => left.name.localeCompare(right.name));

const lines = [
  "# Node Dependency Licenses",
  "",
  "Generated from `web/package-lock.json`; review `UNKNOWN` entries before release.",
  "",
  "| Package | Version | License |",
  "| --- | --- | --- |",
  ...rows.map((row) => `| ${row.name} | ${row.version} | ${row.license} |`),
  "",
];

if (rows.some((row) => row.license === "UNKNOWN")) {
  process.exitCode = 1;
}
await writeFile(new URL("../docs/NODE_LICENSES.md", import.meta.url), lines.join("\n"), "utf8");
