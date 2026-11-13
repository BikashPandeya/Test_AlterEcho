import { expect, test } from "@playwright/test";

test("main navigation, health, filters, and synchronized candidate focus", async ({ page, request }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(page.getByText("3 real Earth sites available")).toBeVisible();
  const health = await request.get("http://127.0.0.1:8000/api/health");
  expect(health.ok()).toBeTruthy();
  expect((await health.json()).data_mode).toBe("mixed");
  await expect(page.getByTestId("candidate-earth-atacama")).toBeVisible();

  await page.getByRole("button", { name: /Upper Mustang/ }).click();
  await expect(page.getByTestId("selected-candidate-details").getByRole("heading", { name: "Upper Mustang" })).toBeVisible();
  await page.getByRole("button", { name: /^All/ }).click();
  await page.getByRole("button", { name: /Danakil Depression/ }).click();
  await expect(page.getByTestId("selected-candidate-details").getByRole("heading", { name: "Danakil Depression" })).toBeVisible();
  await expect(page.getByTestId("candidate-earth-danakil").getByRole("checkbox")).toBeDisabled();

  await page.getByRole("button", { name: /Real data/ }).click();
  await expect(page.getByTestId("candidate-earth-upper-mustang")).toBeVisible();
  await expect(page.getByTestId("candidate-earth-danakil")).toHaveCount(0);
  await page.getByRole("button", { name: /^All/ }).click();

  await page.getByRole("button", { name: "Mars" }).click();
  await expect(page.getByText("PHASE 3 REFERENCE · REAL DEM")).toBeVisible();
  await page.getByRole("button", { name: "Moon" }).click();
  await expect(page.getByRole("heading", { name: "Moon analysis coming in a later phase." })).toBeVisible();
  expect(errors).toEqual([]);
});

test("real result is honest, clears on focus change, and downloads valid JSON", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("candidate-earth-atacama")).toBeVisible();
  await expect(page.getByRole("button", { name: "Compare 3 sites" })).toBeVisible();
  await page.getByRole("button", { name: "Compare 3 sites" }).click();
  const result = page.getByTestId("result-earth-atacama");
  await expect(result).toContainText("REAL DEM");
  await expect(result).toContainText("Processing runs:");
  const downloadPromise = page.waitForEvent("download");
  await result.getByRole("button", { name: "Download result JSON" }).click();
  const download = await downloadPromise;
  const stream = await download.createReadStream();
  const chunks: Buffer[] = [];
  for await (const chunk of stream) chunks.push(Buffer.from(chunk));
  const payload = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  expect(payload.comparison_classification).toBe("real_comparison");
  expect(payload.provenance.notice).toMatch(/processed elevation datasets/);

  await page.getByRole("button", { name: /Upper Mustang/ }).click();
  await expect(page.getByTestId("selected-candidate-details")).toContainText("Upper Mustang");
  await expect(page.getByTestId("result-earth-atacama")).toHaveCount(0);
});

test("API unavailable state is understandable", async ({ page }) => {
  await page.route("http://localhost:8000/api/**", (route) => route.abort());
  await page.route("http://127.0.0.1:8000/api/**", (route) => route.abort());
  await page.goto("/");
  await expect(page.getByText("Backend unavailable", { exact: true })).toBeVisible();
  await expect(page.getByText(/Candidate catalog unavailable|No backend candidates/).first()).toBeVisible();
});

test("comparison failure preserves selection and offers retry", async ({ page }) => {
  await page.route("http://localhost:8000/api/discover", (route) => route.abort());
  await page.goto("/");
  await page.getByRole("button", { name: "Compare 3 sites" }).click();
  await expect(page.getByText("Comparison request failed.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Retry comparison" })).toBeVisible();
  await expect(page.getByText("3 real sites selected")).toBeVisible();
});
