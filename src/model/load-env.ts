import { config as loadDotenv } from "dotenv";

let hasLoadedEnvFiles = false;

export function loadRuntimeEnvFiles(): void {
  if (hasLoadedEnvFiles) {
    return;
  }

  loadDotenv({
    path: ".env.local",
  });

  hasLoadedEnvFiles = true;
}
