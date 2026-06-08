import { Router } from "express";
import { getExecuteCount } from "../lib/store.js";

const router = Router();

router.get("/v5/services/lonelyhub", (req, res) => {
  res.status(200).json({"Name": "Lonely Hub", "Total Execute": getExecuteCount()});
});

router.get("/v5/services/lonelyhub/", (req, res) => {
  res.status(200).json({"Name": "Lonely Hub", "Total Execute": getExecuteCount()});
});

export default router;
