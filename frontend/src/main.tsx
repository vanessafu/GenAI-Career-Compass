import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { CareerCompassApp } from "@/components/compass/CareerCompassApp";
import "./styles.css";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element #root not found");
}

createRoot(rootElement).render(
  <StrictMode>
    <CareerCompassApp />
  </StrictMode>,
);
