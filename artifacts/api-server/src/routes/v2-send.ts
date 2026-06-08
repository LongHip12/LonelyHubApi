import { Router } from "express";
import { checkRateLimit } from "../lib/rateLimiter.js";

const router = Router();

const WEBHOOKS: Record<string, string> = {
  mirage: "https://discord.com/api/webhooks/1513404305325953055/tbj3rwOS_51utpyqnlSMTQATkA2iY2xlOSc3ZfnngqpGrFmyBl2e8yWhtVs9KO996dNq",
  prehistoric: "https://discord.com/api/webhooks/1513404845024083998/8XYS6f5qT2DtEhKVUx46LC2tGhTOQwgk3kCsvNLnVBoDTkK6P9-FcnHw7QflO3NBiIpD",
  kitsune: "https://discord.com/api/webhooks/1513405002138386432/ok5BqNmL5ppcQJLTfbwjrH52FcsUdYFuiVro83YeCfWnU-Jwi4zpgcXXVYPsl_vR8OHL",
  fullmoon: "https://discord.com/api/webhooks/1513405097747546182/jtrsHlyZmrwofPPiMplTzgwgWYcW5cSjfEZfTA4nMenyxh92mBxaIGejPP7GQmx1x6K_",
  nearmoon: "https://discord.com/api/webhooks/1513405176466116711/YRDfrcRky6nyZPpaABXDt-RUDxR0itaWKAoCmAjSCyAsXrMgL61lRyFsVhlW1Laj42dV",
  ripindra: "https://discord.com/api/webhooks/1513405295676756038/DpRkeOhzq7UfKE0JiLFzpzVGJZTZF_DpnhAi_Nv0abEwrUN4I9kK_DG4dZiBAB-bOoOC",
  doughking: "https://discord.com/api/webhooks/1513405365545472070/_Cqy7jwKBr9DwCBum8mu7UEf3P-2Biq4aXwfCGSSAZCDspDljY60TJSa8BpXfLQknXWx",
  katakuri: "https://discord.com/api/webhooks/1513405454577959083/YdDrA5o4_kSSJD3ALoG0gmafphsokXoo4VdSK4c28UTU8ZBjVOK1waTEBzoIQnbtY6hs",
  tyrant: "https://discord.com/api/webhooks/1513405533858697277/pbaTKeGDhVFsTIneeLpMojloFRHYyDagI4EtQ1AX-79pEgLstUgfNtRlk55NOaXlZZR-",
  darkbeard: "https://discord.com/api/webhooks/1513405620789710878/YCeG3r2Bwv_i_3vvKFsYUgZ_rr4FomFiCSB3oaco0_i4CitD6JCGV91ymBht--ig6dge",
  soulreaper: "https://discord.com/api/webhooks/1513405697692401705/sasrbmrq03Fy8KQn19iWccGu1Wwpegf5d5KrFGiNNm4Rbw9Qrl5jMWsG_zprNwmdqpuq",
  cursedcaptain: "https://discord.com/api/webhooks/1513405788360806480/6Jzv4Ywvc7YIF8vOsL73hqQ5CZfnMEyB32eDwHr8v9flCz8vn-vrH3Ozy5htt3HrppL9",
  swordlegendary: "https://discord.com/api/webhooks/1513405894208127016/tOL0AyzKhN3Ef3B5dTQF3OV9mkxmUSQDbjzoY8S0fO0Um-b_FWRuClkCI7AtLERk9oxZ",
  hakilegendary: "https://discord.com/api/webhooks/1513405968405368982/GHyo--6s8dZadjw-hVOJzpCGxWsdmAWamzLvW9pmH1LmxH7jnRaZxQPaJKJqVph6XLts",
};

const BLOCKED = ["@everyone", "@here", "spam", "spammed", "raidded", "@"];

function containsBlocked(obj: unknown): boolean {
  const str = JSON.stringify(obj).toLowerCase();
  return BLOCKED.some((b) => str.includes(b.toLowerCase()));
}

router.post("/v2/send/:name", async (req, res) => {
  const { name } = req.params;
  const webhook = WEBHOOKS[name.toLowerCase()];
  if (!webhook) {
    res.status(404).json({"error": "Unknown endpoint"});
    return;
  }

  const ip = (req.headers["x-forwarded-for"] as string)?.split(",")[0].trim() ?? req.ip ?? "unknown";
  if (!checkRateLimit(`v2:${name}:${ip}`, 30)) {
    res.status(429).json({"error": "Rate limit exceeded. Max 30 requests per minute."});
    return;
  }

  const body = req.body as Record<string, unknown>;
  if (!body.embeds || !Array.isArray(body.embeds) || body.embeds.length === 0) {
    res.status(400).json({"error": "Only embeds are allowed."});
    return;
  }

  if (containsBlocked(body)) {
    res.status(403).json({"error": "Payload contains forbidden content."});
    return;
  }

  const discordRes = await fetch(webhook, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({embeds: body.embeds}),
  });

  if (!discordRes.ok) {
    const text = await discordRes.text();
    res.status(discordRes.status).json({"error": "Discord error", "detail": text});
    return;
  }

  res.status(200).json({"success": true, "message": "Sent to Discord."});
});

export default router;
