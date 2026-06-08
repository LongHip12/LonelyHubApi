import { Router } from "express";
import { getExecuteCount, incrementExecuteCount } from "../lib/store.js";

const router = Router();

const WEBHOOK = "https://discord.com/api/webhooks/1513412624979591230/WxEwthKabsfJmqVYfGJCJ2S69rKPmXhIbxs-nlk0rEbP2GiV1F6fTXgIOBtFhmLoL2vG";

router.post("/v5/oauth2/execute", async (req, res) => {
  const body = req.body as Record<string, unknown>;
  const required = ["DisplayName", "Username", "UserID", "Executor", "HWID", "PlaceID", "JobID", "ScriptJoin"];
  const missing = required.filter((k) => body[k] === undefined || body[k] === null || body[k] === "");
  if (missing.length > 0) {
    res.status(400).json({"error": "Missing required fields", "missing": missing});
    return;
  }

  const totalExecute = incrementExecuteCount();

  const DisplayName = String(body.DisplayName);
  const Username = String(body.Username);
  const UserID = String(body.UserID);
  const Executor = String(body.Executor);
  const HWID = String(body.HWID);
  const PlaceID = String(body.PlaceID);
  const JobID = String(body.JobID);

  const payload = {
    username: "Lonely Hub",
    avatar_url: "https://i.imgur.com/xY7M2iE.jpeg",
    embeds: [
      {
        title: "Roblox Account Information",
        url: `https://www.roblox.com/users/${UserID}`,
        description: `Display Name: **${DisplayName}**`,
        color: 0x00ffff,
        thumbnail: {url: `https://www.roblox.com/headshot-thumbnail/image?userId=${UserID}&width=420&height=420&format=png`},
        fields: [
          {name: "[👤] User Name", value: `\`\`\`\n${Username}\n\`\`\``, inline: true},
          {name: "[🆔] User ID", value: `\`\`\`\n${UserID}\n\`\`\``, inline: true},
          {name: "[🖥️] Executor", value: `\`\`\`\n${Executor}\n\`\`\``, inline: true},
          {name: "[🧬] HWID", value: `\`\`\`\n${HWID}\n\`\`\``, inline: true},
          {name: "[🌏] Place ID", value: `\`\`\`\n${PlaceID}\n\`\`\``, inline: true},
          {name: "[🔗] Job ID", value: `\`\`\`\n${JobID}\n\`\`\``, inline: true},
          {name: "[📜] Script Join", value: `\`\`\`lua\ngame:GetService("TeleportService"):TeleportToPlaceInstance(${PlaceID}, "${JobID}", game.Players.LocalPlayer)\`\`\``, inline: false},
          {name: "[🎮] Type Script", value: "```\nMain Silent Assassins\n```", inline: false},
          {name: "[🚀] Total Execute", value: `\`\`\`\n${totalExecute}\n\`\`\``, inline: false},
        ],
      },
    ],
  };

  const discordRes = await fetch(WEBHOOK, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });

  if (!discordRes.ok) {
    const text = await discordRes.text();
    res.status(discordRes.status).json({"error": "Discord error", "detail": text});
    return;
  }

  res.status(200).json({"success": true, "totalExecute": totalExecute});
});

export default router;
