import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "./index.css";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Applications from "./pages/Applications";
import JobSearch from "./pages/JobSearch";
import ResumeReview from "./pages/ResumeReview";
import Chat from "./pages/Chat";
import Settings from "./pages/Settings";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/applications" element={<Applications />} />
          <Route path="/search" element={<JobSearch />} />
          <Route path="/resume" element={<ResumeReview />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
