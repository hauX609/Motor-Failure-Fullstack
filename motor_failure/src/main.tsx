import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import { validateFrontendConfig } from "@/lib/runtime";
import { setupClientErrorHandlers } from "@/lib/logger";
import { logger } from "@/lib/logger";

validateFrontendConfig();
setupClientErrorHandlers();
logger.info("Frontend booted");

createRoot(document.getElementById("root")!).render(<App />);
