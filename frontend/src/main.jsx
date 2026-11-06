import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/inter"; // Inter incluida en el proyecto (funciona sin internet)
import "./index.css";
import App from "./App.jsx";
import { activarValidacionEnEspanol } from "./utils/validacionEs";

activarValidacionEnEspanol();

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>
);
