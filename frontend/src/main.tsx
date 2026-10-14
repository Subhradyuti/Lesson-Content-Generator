import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import "./index.css";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Layout } from "./components/Layout";
import { ToastViewport } from "./components/Toast";
import { ThemeProvider } from "./context/ThemeContext";
import { DashboardPage } from "./pages/Dashboard";
import { GeneratePage } from "./pages/Generate";
import { HistoryPage } from "./pages/History";
import { RunDetailPage } from "./pages/RunDetail";
import { NotFoundPage } from "./pages/NotFound";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <ErrorBoundary>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<DashboardPage />} />
              <Route path="generate" element={<GeneratePage />} />
              <Route path="history" element={<HistoryPage />} />
              <Route path="runs/:runId" element={<RunDetailPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
          <ToastViewport />
        </BrowserRouter>
      </ErrorBoundary>
    </ThemeProvider>
  </StrictMode>,
);
