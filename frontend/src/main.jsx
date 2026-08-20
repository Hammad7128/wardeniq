import React from "react";
import ReactDOM from "react-dom/client";
import App from "./app/App.jsx";
import "./styles/tailwind.css";
import "./styles/compat/00-foundation.css";
import "./styles/compat/01-steps-and-forms.css";
import "./styles/compat/02-overlays-and-auth.css";
import "./styles/compat/03-analysis.css";
import "./styles/compat/04-projects-and-coverage.css";
import "./styles/compat/05-theme.css";
import "./styles/compat/06-feedback-and-loaders.css";
import "./styles/compat/07-dashboard-config-sidebar.css";
import "./styles/app.css";

// Font 

import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";

const root = document.getElementById("root");

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
