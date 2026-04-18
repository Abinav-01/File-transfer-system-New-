import { expect, test, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const fileBody = Buffer.from("DropVault browser journey\n");
const sample = { name: "journey.txt", mimeType: "text/plain", buffer: fileBody };
const projectRoot = resolve(__dirname, "../..");

async function uploadFromBrowser(page: Page, options: { expiration?: string; limit?: string; password?: string } = {}) {
  await page.goto("/");
  const fileInput = page.getByTestId("upload-file-input");
  await expect(fileInput).toHaveAttribute("data-ready", "true");
  await fileInput.setInputFiles(sample);
  await expect(page.getByText("journey.txt", { exact: true })).toBeVisible();
  if (options.expiration) await page.getByLabel("Expiration").selectOption(options.expiration);
  if (options.limit) await page.getByLabel("Maximum downloads").selectOption(options.limit);
  if (options.password) {
    await page.getByRole("checkbox", { name: /Password protection/ }).check();
    await page.getByLabel("Password", { exact: true }).fill(options.password);
  }
  await page.getByRole("button", { name: "Create Secure Link" }).click();
  await expect(page).toHaveURL(/\/success\/[0-9a-f-]+$/);
  await expect(page.getByRole("heading", { name: "Your secure link is ready" })).toBeVisible();
  const link = await page.getByRole("textbox", { name: "Share link" }).inputValue();
  expect(link).toMatch(/\/d\/[A-Za-z0-9_-]+$/);
  return link;
}

async function verifyDownload(page: Page) {
  const pending = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download File" }).click();
  const download = await pending;
  expect(download.suggestedFilename()).toBe("journey.txt");
  expect(await readFile(await download.path())).toEqual(fileBody);
  await expect(page.getByText("Your download has started.")).toBeVisible();
}

test("normal file: upload, share, download", async ({ page }) => {
  const link = await uploadFromBrowser(page, { expiration: "360", limit: "5" });
  await page.goto(link);
  await expect(page.getByRole("heading", { name: "A file is ready for you" })).toBeVisible();
  await expect(page.getByText("journey.txt", { exact: true })).toBeVisible();
  await verifyDownload(page);
});

test("password: wrong password gives an error, correct password downloads", async ({ page }) => {
  const link = await uploadFromBrowser(page, { password: "browser-test-secret" });
  await page.goto(link);
  await expect(page.getByLabel("Password required")).toBeVisible();
  await page.getByLabel("Password required").fill("incorrect");
  await page.getByRole("button", { name: "Download File" }).click();
  await expect(page.locator(".error-message[role='alert']")).toContainText("Incorrect password");
  await page.getByLabel("Password required").fill("browser-test-secret");
  await verifyDownload(page);
});

test("download limit: one succeeds and the next attempt is rejected", async ({ page }) => {
  const link = await uploadFromBrowser(page, { limit: "1" });
  const token = new URL(link).pathname.split("/").pop();
  await page.goto(link);
  await expect(page.getByRole("button", { name: "Download File" })).toBeVisible();
  await verifyDownload(page);
  const second = await page.request.post(`/backend/api/files/${token}/download`, { data: {} });
  expect(second.status()).toBe(410);
  expect((await second.json()).detail).toBe("Download limit reached");
  await page.reload();
  await expect(page.getByRole("heading", { name: "This file has reached its download limit." })).toBeVisible();
});

test("delete: dashboard management disables the public link", async ({ page }) => {
  const link = await uploadFromBrowser(page);
  await page.getByRole("link", { name: "My files", exact: true }).click();
  await expect(page.getByRole("article")).toContainText("journey.txt");
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Delete", exact: true }).click();
  await expect(page.getByRole("status")).toHaveText("File deleted.");
  await page.goto(link);
  await expect(page.getByRole("heading", { name: "This file was deleted by its owner." })).toBeVisible();
});

test("expiration: API fixture becomes unavailable when its time passes", async ({ page, request }) => {
  const result = await request.post("/backend/api/uploads", {
    multipart: { file: sample, expires_in: "1" },
  });
  expect(result.status()).toBe(201);
  const created = await result.json() as { id: string; share_token: string };
  execFileSync("docker", ["compose", "-p", "dropvault-e2e", "-f", "docker-compose.e2e.yml",
    "exec", "-T", "backend-e2e", "python", "-m", "tests.fixtures.expire_upload", created.id],
  { cwd: projectRoot, stdio: "pipe" });
  await page.goto(`/d/${created.share_token}`);
  await expect(page.getByRole("heading", { name: "This link has expired." })).toBeVisible();
});
