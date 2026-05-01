import { Router } from "express";
import healthRouter from "./health.js";
import clipflyRouter from "./clipfly.js";
import geminigenRouter from "./geminigen.js";

const router = Router();
router.use(healthRouter);
router.use("/clipfly", clipflyRouter);
router.use("/geminigen", geminigenRouter);
export default router;
