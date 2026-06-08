import { Router } from "express";
import { checkRateLimit } from "../lib/rateLimiter.js";
import { getApiEntry, saveApiEntry } from "../lib/store.js";

const router = Router();

const BLOCKED_V3 = ["@everyone", "@here"];

router.post("/v3/apis", (req, res) => {
  const body = req.body as Record<string, unknown>;
  const apiId = String(body.apiId ?? "").trim();
  const apiName = String(body.apiName ?? "").trim();
  const webhook = String(body.webhook ?? "").trim();
  const rateLimit = Number(body.rateLimit ?? 30);

  if (!apiId || !apiName || !webhook) {
    res.status(400).json({"error": "apiId, apiName, and webhook are required."});
    return;
  }

  saveApiEntry({apiId, apiName, webhook, rateLimit});
  res.status(201).json({"success": true, "apiId": apiId, "apiName": apiName, "endpoint": `/api/v3/${apiId}/send/${apiName}`});
});

router.put("/v3/apis/:apiId", (req, res) => {
  const { apiId } = req.params;
  const existing = getApiEntry(apiId);
  if (!existing) {
    res.status(404).json({"error": "API not found."});
    return;
  }

  const body = req.body as Record<string, unknown>;
  const apiName = String(body.apiName ?? existing.apiName).trim();
  const webhook = String(body.webhook ?? existing.webhook).trim();
  const rateLimit = body.rateLimit !== undefined ? Number(body.rateLimit) : existing.rateLimit;

  saveApiEntry({apiId, apiName, webhook, rateLimit});
  res.status(200).json({"success": true, "apiId": apiId, "apiName": apiName, "endpoint": `/api/v3/${apiId}/send/${apiName}`});
});

router.post("/v3/:apiId/send/:apiName", async (req, res) => {
  const { apiId, apiName } = req.params;
  const entry = getApiEntry(apiId);
  if (!entry || entry.apiName.toLowerCase() !== apiName.toLowerCase()) {
    res.status(404).json({"error": "API not found."});
    return;
  }

  const ip = (req.headers["x-forwarded-for"] as string)?.split(",")[0].trim() ?? req.ip ?? "unknown";
  if (!checkRateLimit(`v3:${apiId}:${ip}`, entry.rateLimit)) {
    res.status(429).json({"error": `Rate limit exceeded. Max ${entry.rateLimit} requests per minute.`});
    return;
  }

  const body = req.body as Record<string, unknown>;
  const bodyStr = JSON.stringify(body);
  if (BLOCKED_V3.some((b) => bodyStr.includes(b))) {
    res.status(403).json({"error": "Payload contains forbidden content."});
    return;
  }

  const headerLines = Object.entries(body)
    .map(([k, v]) => `    + ${k}: ${v}`)
    .join("\n");

  const content = `# API Post Detected!\n- **API Name**: ${entry.apiName}\n- **API ID**: ${apiId}\n- **Headers**:\n${headerLines}`;

  const discordRes = await fetch(entry.webhook, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({content}),
  });

  if (!discordRes.ok) {
    const text = await discordRes.text();
    res.status(discordRes.status).json({"error": "Discord error", "detail": text});
    return;
  }

  res.status(200).json({"success": true});
});

export default router;
