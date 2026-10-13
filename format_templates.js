const fs = require("fs");
const os = require("os");
const path = require("path");
const childProcess = require("child_process");

const files = [
  "admin_attendance.html",
  "admin_leave.html",
  "admin_tasks.html",
  "leave.html",
  "tasks.html",
];
const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "ems-format-"));

try {
  for (const file of files) {
    const sourcePath = path.join("app", "templates", file);
    const source = fs.readFileSync(sourcePath, "utf8");
    const tokens = [];
    const masked = source.replace(
      /\{%[\s\S]*?%\}|\{\{[\s\S]*?\}\}/g,
      (value) => {
        const token = `EMSJINJATOKEN${tokens.length}END`;
        tokens.push(value);
        return token;
      },
    );
    const tempPath = path.join(tempDir, file);
    fs.writeFileSync(tempPath, masked, "utf8");
    childProcess.execFileSync(
      "npx",
      ["--yes", "prettier@3.6.2", "--write", "--parser", "html", tempPath],
      { shell: true, stdio: "inherit" },
    );
    const formatted = fs
      .readFileSync(tempPath, "utf8")
      .replace(/EMSJINJATOKEN(\d+)END/g, (_, index) => tokens[Number(index)]);
    fs.writeFileSync(sourcePath, formatted, "utf8");
  }
} finally {
  fs.rmSync(tempDir, { recursive: true, force: true });
}