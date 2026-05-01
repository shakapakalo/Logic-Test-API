import app from "./app.js";
import { logger } from "./lib/logger.js";

const PORT = Number(process.env.PORT ?? 3000);

app.listen(PORT, () => {
  logger.info({ port: PORT }, "AI API Server started");
});
