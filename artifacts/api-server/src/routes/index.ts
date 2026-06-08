import { Router, type IRouter } from "express";
import healthRouter from "./health.js";
import v2SendRouter from "./v2-send.js";
import v1BloxfruitRouter from "./v1-bloxfruit.js";
import v5Oauth2Router from "./v5-oauth2.js";
import v5ServicesRouter from "./v5-services.js";
import v3ApiRouter from "./v3-api.js";

const router: IRouter = Router();

router.use(healthRouter);
router.use(v2SendRouter);
router.use(v1BloxfruitRouter);
router.use(v5Oauth2Router);
router.use(v5ServicesRouter);
router.use(v3ApiRouter);

export default router;
