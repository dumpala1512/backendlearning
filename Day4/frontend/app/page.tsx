"use client";

import React, { useState, useEffect, useMemo } from "react";

interface UserProfile {
  id: string;
  username: string;
  email: string;
  role: string;
}

interface Review {
  id: string;
  film_id: string;
  user_id: string;
  reviewer_display_name: string;
  rating: number;
  review: string;
  created_at?: string;
}

interface Film {
  id: string;
  title: string;
  director: string;
  releaseYear: number;
  genre: string;
  description: string;
  total_reviews?: number;
  review_count?: number;
  average_rating?: number | null;
}

interface TelemetryMeta {
  endpoint: string;
  status: number;
  requestId: string | null;
  processTime: string | null;
  timestamp: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function FilmReviewPortal() {
  // Navigation View: Dashboard vs Jinja UI Embed
  const [activeTab, setActiveTab] = useState<"dashboard" | "embed">("dashboard");
  const [mounted, setMounted] = useState<boolean>(false);

  // Dynamic Auth State
  const [token, setToken] = useState<string>("");
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [authLoading, setAuthLoading] = useState<boolean>(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [loginEmail, setLoginEmail] = useState<string>("bob@example.com");
  const [loginPassword, setLoginPassword] = useState<string>("CanWeFixIt123!");
  const [showAuthModal, setShowAuthModal] = useState<boolean>(false);

  // Dynamic Films Data
  const [films, setFilms] = useState<Film[]>([]);
  const [filmsLoading, setFilmsLoading] = useState<boolean>(false);
  const [filmsError, setFilmsError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedFilm, setSelectedFilm] = useState<Film | null>(null);

  // Dynamic Reviews Data
  const [filmReviews, setFilmReviews] = useState<Review[]>([]);
  const [reviewsLoading, setReviewsLoading] = useState<boolean>(false);

  // Review Form State
  const [rating, setRating] = useState<number | string>(10);
  const [reviewerDisplayName, setReviewerDisplayName] = useState<string>("");
  const [reviewComment, setReviewComment] = useState<string>("");
  const [submittingReview, setSubmittingReview] = useState<boolean>(false);
  const [reviewFeedback, setReviewFeedback] = useState<{
    type: "success" | "error" | "info";
    message: string;
  } | null>(null);

  // Telemetry & Diagnostic Headers
  const [telemetry, setTelemetry] = useState<TelemetryMeta | null>(null);
  const [corsVerified, setCorsVerified] = useState<boolean>(false);

  // Helper to capture response telemetry headers
  const captureTelemetry = (endpoint: string, res: Response) => {
    const reqId = res.headers.get("x-request-id") || res.headers.get("X-Request-ID");
    const procTime = res.headers.get("x-process-time") || res.headers.get("X-Process-Time");
    const allowOrigin = res.headers.get("access-control-allow-origin");

    setTelemetry({
      endpoint,
      status: res.status,
      requestId: reqId,
      processTime: procTime,
      timestamp: new Date().toLocaleTimeString(),
    });

    if (allowOrigin === "http://localhost:3000") {
      setCorsVerified(true);
    }
  };

  // 1. Dynamic Authentication (/login & /me)
  const handleLogin = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setAuthLoading(true);
    setAuthError(null);

    try {
      const loginRes = await fetch(`${API_BASE_URL}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email_or_username: loginEmail,
          password: loginPassword,
        }),
      });

      captureTelemetry("POST /login", loginRes);

      if (!loginRes.ok) {
        const errJson = await loginRes.json().catch(() => ({}));
        throw new Error(errJson.message || `Login failed (${loginRes.status})`);
      }

      const tokenData = await loginRes.json();
      const accessToken = tokenData.access_token;
      setToken(accessToken);

      // Fetch dynamic profile from /me
      const profileRes = await fetch(`${API_BASE_URL}/me`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });

      captureTelemetry("GET /me", profileRes);

      if (profileRes.ok) {
        const profile: UserProfile = await profileRes.json();
        setUserProfile(profile);
        setReviewerDisplayName(profile.username);
      } else {
        const fallback: UserProfile = {
          id: tokenData.user_id,
          username: tokenData.username,
          email: loginEmail,
          role: tokenData.role,
        };
        setUserProfile(fallback);
        setReviewerDisplayName(fallback.username);
      }
      setShowAuthModal(false);
    } catch (err: any) {
      setAuthError(err.message || "Failed to log in");
    } finally {
      setAuthLoading(false);
    }
  };

  // Logout: calls POST /logout to revoke refresh tokens and clears local session
  const handleLogout = async () => {
    if (token) {
      try {
        const res = await fetch(`${API_BASE_URL}/logout`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        });
        captureTelemetry("POST /logout", res);
      } catch (err) {
        console.error("Logout request failed:", err);
      }
    }
    setToken("");
    setUserProfile(null);
    setReviewerDisplayName("");
    setReviewFeedback(null);
    setShowAuthModal(false);
  };

  // Initial login on mount
  useEffect(() => {
    setMounted(true);
    handleLogin();
  }, []);

  // 2. Dynamic Films Catalog (/api/v1/films)
  const loadFilms = async () => {
    setFilmsLoading(true);
    setFilmsError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/films?page=1&page_size=30`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      captureTelemetry("GET /api/v1/films", res);

      if (!res.ok) {
        throw new Error(`Failed to load films (HTTP ${res.status})`);
      }

      const data = await res.json();
      const items: Film[] = data.items || data;
      setFilms(items);

      // Keep current selection or pick first
      if (items.length > 0) {
        setSelectedFilm((prev) => (prev ? items.find((f) => f.id === prev.id) || items[0] : items[0]));
      }
    } catch (err: any) {
      setFilmsError(err.message || "Failed to load film catalogue");
    } finally {
      setFilmsLoading(false);
    }
  };

  useEffect(() => {
    loadFilms();
  }, [token]);

  // 3. Dynamic Reviews for Selected Film (/films/{id}/reviews)
  const loadFilmReviews = async (filmId: string) => {
    setReviewsLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/films/${filmId}/reviews`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      captureTelemetry(`GET /films/${filmId}/reviews`, res);

      if (res.ok) {
        const data = await res.json();
        setFilmReviews(data.items || data || []);
      } else {
        setFilmReviews([]);
      }
    } catch (err) {
      console.error("Error loading reviews:", err);
      setFilmReviews([]);
    } finally {
      setReviewsLoading(false);
    }
  };

  useEffect(() => {
    if (selectedFilm?.id) {
      loadFilmReviews(selectedFilm.id);
    }
  }, [selectedFilm?.id, token]);

  // 4. Dynamic Review Submission (/films/{id}/reviews)
  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFilm) {
      setReviewFeedback({ type: "error", message: "Please select a target film first." });
      return;
    }
    if (!token || !userProfile) {
      setReviewFeedback({
        type: "error",
        message: "You must be authenticated with role 'critic' or 'admin' to submit reviews.",
      });
      return;
    }
    if (reviewComment.trim().length < 50) {
      setReviewFeedback({
        type: "error",
        message: `Review text must be at least 50 characters (currently ${reviewComment.trim().length}).`,
      });
      return;
    }

    const numericRating = Number(rating);
    if (!rating || isNaN(numericRating) || numericRating < 1 || numericRating > 10 || !Number.isInteger(numericRating)) {
      setReviewFeedback({
        type: "error",
        message: "Please enter a valid rating between 1 and 10.",
      });
      return;
    }

    setSubmittingReview(true);
    setReviewFeedback(null);

    try {
      const targetUrl = `${API_BASE_URL}/films/${selectedFilm.id}/reviews`;
      const res = await fetch(targetUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          film_id: selectedFilm.id,
          rating: numericRating,
          review: reviewComment.trim(),
          reviewer_display_name: reviewerDisplayName.trim() || userProfile.username,
          user_id: userProfile.id,
        }),
      });

      captureTelemetry(`POST /films/${selectedFilm.id}/reviews`, res);

      const data = await res.json();

      if (!res.ok) {
        setReviewFeedback({
          type: "error",
          message: data.message || `Failed to submit review (HTTP ${res.status})`,
        });
      } else {
        const procTime = res.headers.get("x-process-time") || res.headers.get("X-Process-Time");
        setReviewFeedback({
          type: "info",
          message: `Review submitted instantly (HTTP 201 Created • ${procTime || "0ms"}). Recalculating film stats in background...`,
        });
        setReviewComment("");

        // Refresh stats from route after background task executes
        setTimeout(async () => {
          try {
            const filmRes = await fetch(`${API_BASE_URL}/api/v1/films/${selectedFilm.id}`, {
              headers: token ? { Authorization: `Bearer ${token}` } : {},
            });
            if (filmRes.ok) {
              const updatedFilm: Film = await filmRes.json();
              setSelectedFilm(updatedFilm);
              setFilms((prev) => prev.map((f) => (f.id === updatedFilm.id ? updatedFilm : f)));
              await loadFilmReviews(updatedFilm.id);
              const count = updatedFilm.total_reviews ?? updatedFilm.review_count ?? 0;
              const avg = updatedFilm.average_rating ? `★ ${updatedFilm.average_rating}` : "Unrated";
              setReviewFeedback({
                type: "success",
                message: `Background task completed! Updated stats: ${count} reviews • Rating ${avg}`,
              });
            }
          } catch (err) {
            console.error("Error refreshing stats:", err);
          }
        }, 800);
      }
    } catch (err: any) {
      setReviewFeedback({ type: "error", message: `Submission error: ${err.message}` });
    } finally {
      setSubmittingReview(false);
    }
  };

  // Filtered film list
  const filteredFilms = useMemo(() => {
    if (!searchQuery.trim()) return films;
    const q = searchQuery.toLowerCase();
    return films.filter(
      (f) =>
        f.title.toLowerCase().includes(q) ||
        f.director.toLowerCase().includes(q) ||
        f.genre.toLowerCase().includes(q)
    );
  }, [films, searchQuery]);

  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: "#070b14",
        color: "#f8fafc",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Top Navbar */}
      <header
        style={{
          borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
          backgroundColor: "rgba(11, 16, 29, 0.8)",
          backdropFilter: "blur(12px)",
          position: "sticky",
          top: 0,
          zIndex: 50,
          padding: "0.75rem 1.5rem",
        }}
      >
        <div
          style={{
            maxWidth: "1400px",
            margin: "0 auto",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "1rem",
          }}
        >
          {/* Brand */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.85rem" }}>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "10px",
                background: "linear-gradient(135deg, #6366f1 0%, #06b6d4 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 4px 14px rgba(99, 102, 241, 0.35)",
              }}
            >
              <span style={{ fontSize: "1.1rem", fontWeight: "800", color: "#fff" }}>🎬</span>
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span style={{ fontSize: "1.1rem", fontWeight: "700", letterSpacing: "-0.01em" }}>
                  CineMetric
                </span>
                <span
                  style={{
                    fontSize: "0.65rem",
                    fontWeight: "700",
                    padding: "0.15rem 0.45rem",
                    borderRadius: "9999px",
                    background: "rgba(99, 102, 241, 0.18)",
                    border: "1px solid rgba(99, 102, 241, 0.4)",
                    color: "#a5b4fc",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                  }}
                >
                  Day 4 Engine
                </span>
              </div>
              <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
                Film Review Platform • Async Background Tasks & Strict CORS
              </div>
            </div>
          </div>

          {/* View Toggle */}
          <div
            style={{
              display: "flex",
              backgroundColor: "rgba(255, 255, 255, 0.05)",
              padding: "0.25rem",
              borderRadius: "10px",
              border: "1px solid rgba(255, 255, 255, 0.06)",
            }}
          >
            <button
              onClick={() => setActiveTab("dashboard")}
              style={{
                padding: "0.45rem 1rem",
                borderRadius: "8px",
                border: "none",
                fontSize: "0.8rem",
                fontWeight: "600",
                cursor: "pointer",
                transition: "all 0.15s ease",
                backgroundColor: activeTab === "dashboard" ? "#6366f1" : "transparent",
                color: activeTab === "dashboard" ? "#ffffff" : "#94a3b8",
                boxShadow: activeTab === "dashboard" ? "0 2px 8px rgba(99, 102, 241, 0.4)" : "none",
              }}
            >
              Film Explorer & Reviews
            </button>
            <button
              onClick={() => setActiveTab("embed")}
              style={{
                padding: "0.45rem 1rem",
                borderRadius: "8px",
                border: "none",
                fontSize: "0.8rem",
                fontWeight: "600",
                cursor: "pointer",
                transition: "all 0.15s ease",
                backgroundColor: activeTab === "embed" ? "#6366f1" : "transparent",
                color: activeTab === "embed" ? "#ffffff" : "#94a3b8",
                boxShadow: activeTab === "embed" ? "0 2px 8px rgba(99, 102, 241, 0.4)" : "none",
              }}
            >
              Server HTMX UI (/ui/films)
            </button>
          </div>

          {/* User Session Bar */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            {!mounted ? (
              <span style={{ fontSize: "0.8rem", color: "#64748b" }}>Loading session...</span>
            ) : userProfile ? (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.6rem",
                  backgroundColor: "rgba(16, 185, 129, 0.1)",
                  border: "1px solid rgba(16, 185, 129, 0.25)",
                  padding: "0.35rem 0.75rem",
                  borderRadius: "9999px",
                }}
              >
                <div
                  style={{
                    width: "8px",
                    height: "8px",
                    borderRadius: "50%",
                    backgroundColor: "#10b981",
                    boxShadow: "0 0 8px #10b981",
                  }}
                />
                <span style={{ fontSize: "0.8rem", fontWeight: "600", color: "#6ee7b7" }}>
                  {userProfile.username}
                </span>
                <span
                  style={{
                    fontSize: "0.7rem",
                    padding: "0.1rem 0.4rem",
                    borderRadius: "4px",
                    backgroundColor: "rgba(16, 185, 129, 0.2)",
                    color: "#a7f3d0",
                    fontWeight: "600",
                  }}
                >
                  {userProfile.role}
                </span>
              </div>
            ) : (
              <span style={{ fontSize: "0.8rem", color: "#f87171" }}>
                {authLoading ? "Authenticating..." : "Disconnected"}
              </span>
            )}

            {mounted && userProfile && (
              <button
                onClick={handleLogout}
                style={{
                  backgroundColor: "rgba(239, 68, 68, 0.15)",
                  border: "1px solid rgba(239, 68, 68, 0.35)",
                  color: "#fca5a5",
                  fontSize: "0.75rem",
                  fontWeight: "600",
                  padding: "0.45rem 0.8rem",
                  borderRadius: "8px",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
              >
                Log Out
              </button>
            )}

            <button
              onClick={() => setShowAuthModal(!showAuthModal)}
              style={{
                backgroundColor: "rgba(255, 255, 255, 0.06)",
                border: "1px solid rgba(255, 255, 255, 0.12)",
                color: "#e2e8f0",
                fontSize: "0.75rem",
                fontWeight: "600",
                padding: "0.45rem 0.8rem",
                borderRadius: "8px",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
            >
              {showAuthModal ? "Close" : mounted && userProfile ? "Switch Account" : "Sign In"}
            </button>
          </div>
        </div>

        {/* Expandable Switch Account Modal */}
        {showAuthModal && (
          <div
            style={{
              maxWidth: "1400px",
              margin: "0.75rem auto 0 auto",
              padding: "1rem",
              backgroundColor: "#0d1424",
              borderRadius: "10px",
              border: "1px solid rgba(99, 102, 241, 0.3)",
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "1rem",
            }}
          >
            <div>
              <div style={{ fontSize: "0.85rem", fontWeight: "600", color: "#e2e8f0" }}>
                Authenticate via POST /login & GET /me
              </div>
              <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
                Log in as an Admin or Critic to submit reviews with full RBAC authorization.
              </div>
            </div>

            <form onSubmit={handleLogin} style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
              <input
                type="text"
                placeholder="Email / Username"
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                style={{
                  backgroundColor: "rgba(255, 255, 255, 0.05)",
                  border: "1px solid rgba(255, 255, 255, 0.15)",
                  color: "#fff",
                  fontSize: "0.8rem",
                  padding: "0.4rem 0.75rem",
                  borderRadius: "6px",
                  width: "180px",
                }}
              />
              <input
                type="password"
                placeholder="Password"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                style={{
                  backgroundColor: "rgba(255, 255, 255, 0.05)",
                  border: "1px solid rgba(255, 255, 255, 0.15)",
                  color: "#fff",
                  fontSize: "0.8rem",
                  padding: "0.4rem 0.75rem",
                  borderRadius: "6px",
                  width: "150px",
                }}
              />
              <button
                type="submit"
                disabled={authLoading}
                style={{
                  backgroundColor: "#6366f1",
                  border: "none",
                  color: "#fff",
                  fontSize: "0.8rem",
                  fontWeight: "600",
                  padding: "0.45rem 1rem",
                  borderRadius: "6px",
                  cursor: "pointer",
                }}
              >
                {authLoading ? "Verifying..." : "Sign In"}
              </button>
            </form>
            {authError && <div style={{ width: "100%", fontSize: "0.75rem", color: "#f87171" }}>{authError}</div>}
          </div>
        )}
      </header>

      {/* Sleek Live Telemetry Strip */}
      <section
        style={{
          borderBottom: "1px solid rgba(255, 255, 255, 0.06)",
          backgroundColor: "rgba(15, 23, 42, 0.65)",
          padding: "0.5rem 1.5rem",
        }}
      >
        <div
          style={{
            maxWidth: "1400px",
            margin: "0 auto",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "0.75rem",
            fontSize: "0.75rem",
          }}
        >
          {/* Request ID Badge */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <span style={{ color: "#64748b", fontWeight: "600" }}>X-Request-ID:</span>
            <code
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                color: "#38bdf8",
                backgroundColor: "rgba(56, 189, 248, 0.1)",
                padding: "0.15rem 0.45rem",
                borderRadius: "4px",
                border: "1px solid rgba(56, 189, 248, 0.2)",
              }}
            >
              {telemetry?.requestId ? telemetry.requestId : "Awaiting request..."}
            </code>
          </div>

          {/* Process Time Badge */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <span style={{ color: "#64748b", fontWeight: "600" }}>X-Process-Time:</span>
            <span
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontWeight: "700",
                color: "#10b981",
                backgroundColor: "rgba(16, 185, 129, 0.1)",
                padding: "0.15rem 0.45rem",
                borderRadius: "4px",
                border: "1px solid rgba(16, 185, 129, 0.2)",
              }}
            >
              {telemetry?.processTime ? telemetry.processTime : "-- ms"}
            </span>
          </div>

          {/* CORS Badge */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <span style={{ color: "#64748b", fontWeight: "600" }}>CORS Origin:</span>
            <span
              style={{
                color: corsVerified ? "#c084fc" : "#94a3b8",
                backgroundColor: "rgba(192, 132, 252, 0.1)",
                padding: "0.15rem 0.45rem",
                borderRadius: "4px",
                border: "1px solid rgba(192, 132, 252, 0.2)",
                fontWeight: "600",
              }}
            >
              http://localhost:3000 (Strict Whitelist)
            </span>
          </div>

          {/* Route Status */}
          <div style={{ color: "#64748b" }}>
            Last Route: <span style={{ color: "#94a3b8" }}>{telemetry?.endpoint || "N/A"}</span>{" "}
            {telemetry?.status && (
              <span
                style={{
                  color: telemetry.status < 400 ? "#34d399" : "#f87171",
                  fontWeight: "700",
                }}
              >
                ({telemetry.status})
              </span>
            )}
          </div>
        </div>
      </section>

      {/* Main Workspace */}
      <main
        style={{
          flex: 1,
          maxWidth: "1400px",
          width: "100%",
          margin: "0 auto",
          padding: "1.25rem 1.5rem 2rem 1.5rem",
        }}
      >
        {activeTab === "embed" ? (
          /* Server HTMX Embed View */
          <div
            style={{
              backgroundColor: "rgba(19, 28, 46, 0.6)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              borderRadius: "14px",
              padding: "1rem",
              height: "calc(100vh - 180px)",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.75rem" }}>
              <div style={{ fontSize: "0.9rem", fontWeight: "600", color: "#94a3b8" }}>
                Embedded FastAPI Server Template UI (<code>{API_BASE_URL}/ui/films</code>)
              </div>
              <a
                href={`${API_BASE_URL}/ui/films`}
                target="_blank"
                rel="noreferrer"
                style={{ fontSize: "0.8rem", color: "#6366f1", textDecoration: "underline" }}
              >
                Open in new tab ↗
              </a>
            </div>
            <iframe
              src={`${API_BASE_URL}/ui/films`}
              title="FastAPI HTMX UI"
              style={{
                width: "100%",
                flex: 1,
                border: "none",
                borderRadius: "8px",
                backgroundColor: "#070b14",
              }}
            />
          </div>
        ) : (
          /* Dynamic Dashboard Grid */
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "380px 1fr",
              gap: "1.5rem",
              alignItems: "start",
            }}
          >
            {/* Left Column: Film Catalogue */}
            <section
              style={{
                backgroundColor: "rgba(15, 23, 42, 0.75)",
                border: "1px solid rgba(255, 255, 255, 0.08)",
                borderRadius: "16px",
                padding: "1.25rem",
                display: "flex",
                flexDirection: "column",
                boxShadow: "0 8px 32px rgba(0, 0, 0, 0.3)",
                height: "calc(100vh - 160px)",
                minHeight: "650px",
              }}
            >
              {/* Catalogue Header */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                <div>
                  <h2 style={{ fontSize: "1.05rem", fontWeight: "700", letterSpacing: "-0.01em" }}>
                    Film Catalogue
                  </h2>
                  <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                    {filteredFilms.length} {filteredFilms.length === 1 ? "film" : "films"} loaded from API
                  </span>
                </div>
                <button
                  onClick={loadFilms}
                  disabled={filmsLoading}
                  style={{
                    backgroundColor: "rgba(255, 255, 255, 0.05)",
                    border: "1px solid rgba(255, 255, 255, 0.1)",
                    color: "#94a3b8",
                    padding: "0.35rem 0.65rem",
                    borderRadius: "6px",
                    cursor: "pointer",
                    fontSize: "0.75rem",
                    fontWeight: "600",
                    transition: "all 0.15s ease",
                  }}
                >
                  {filmsLoading ? "..." : "↻ Refresh"}
                </button>
              </div>

              {/* Search Bar */}
              <div style={{ marginBottom: "0.75rem" }}>
                <input
                  type="text"
                  placeholder="Filter by title, genre, director..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "0.55rem 0.85rem",
                    borderRadius: "8px",
                    backgroundColor: "rgba(7, 11, 20, 0.7)",
                    border: "1px solid rgba(255, 255, 255, 0.1)",
                    color: "#f8fafc",
                    fontSize: "0.8rem",
                  }}
                />
              </div>

              {filmsError && (
                <div
                  style={{
                    backgroundColor: "rgba(239, 68, 68, 0.15)",
                    border: "1px solid rgba(239, 68, 68, 0.3)",
                    color: "#fca5a5",
                    padding: "0.6rem",
                    borderRadius: "8px",
                    fontSize: "0.75rem",
                    marginBottom: "0.75rem",
                  }}
                >
                  {filmsError}
                </div>
              )}

              {/* Scrollable Film List */}
              <div
                style={{
                  flex: 1,
                  overflowY: "auto",
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.6rem",
                  paddingRight: "0.3rem",
                  paddingTop: "0.25rem",
                  paddingBottom: "0.5rem",
                }}
              >
                {filteredFilms.length === 0 ? (
                  <div style={{ textAlign: "center", padding: "2rem 1rem", color: "#64748b", fontSize: "0.85rem" }}>
                    {filmsLoading ? "Loading films from /api/v1/films..." : "No matching films found."}
                  </div>
                ) : (
                  filteredFilms.map((film) => {
                    const isSelected = selectedFilm?.id === film.id;
                    const reviewCount = film.total_reviews ?? film.review_count ?? 0;
                    return (
                      <div
                        key={film.id}
                        onClick={() => setSelectedFilm(film)}
                        style={{
                          padding: "0.85rem",
                          borderRadius: "10px",
                          backgroundColor: isSelected
                            ? "rgba(99, 102, 241, 0.15)"
                            : "rgba(11, 16, 29, 0.6)",
                          border: isSelected
                            ? "1px solid #6366f1"
                            : "1px solid rgba(255, 255, 255, 0.05)",
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                          boxShadow: isSelected
                            ? "0 4px 15px rgba(99, 102, 241, 0.2)"
                            : "none",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem" }}>
                          <div style={{ flex: 1 }}>
                            <div
                              style={{
                                fontSize: "0.9rem",
                                fontWeight: "700",
                                color: isSelected ? "#e0e7ff" : "#f1f5f9",
                                lineHeight: "1.25",
                              }}
                            >
                              {film.title}
                            </div>
                            <div style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: "0.2rem" }}>
                              {film.director} • {film.releaseYear}
                            </div>
                          </div>

                          {/* Stats Badges */}
                          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "0.2rem" }}>
                            <span
                              style={{
                                fontSize: "0.7rem",
                                fontWeight: "700",
                                padding: "0.15rem 0.45rem",
                                borderRadius: "6px",
                                backgroundColor:
                                  film.average_rating !== null && film.average_rating !== undefined
                                    ? "rgba(245, 158, 11, 0.2)"
                                    : "rgba(255, 255, 255, 0.06)",
                                color:
                                  film.average_rating !== null && film.average_rating !== undefined
                                    ? "#fbbf24"
                                    : "#64748b",
                                border:
                                  film.average_rating !== null && film.average_rating !== undefined
                                    ? "1px solid rgba(245, 158, 11, 0.3)"
                                    : "1px solid rgba(255, 255, 255, 0.04)",
                              }}
                            >
                              {film.average_rating !== null && film.average_rating !== undefined
                                ? `★ ${film.average_rating}`
                                : "Unrated"}
                            </span>
                            <span style={{ fontSize: "0.68rem", color: "#64748b" }}>
                              {reviewCount} {reviewCount === 1 ? "review" : "reviews"}
                            </span>
                          </div>
                        </div>

                        {film.description && (
                          <p
                            style={{
                              fontSize: "0.75rem",
                              color: "#64748b",
                              marginTop: "0.45rem",
                              overflow: "hidden",
                              display: "-webkit-box",
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: "vertical",
                              lineHeight: "1.35",
                            }}
                          >
                            {film.description}
                          </p>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </section>

            {/* Right Column: Selected Film Spotlight, Review Form & Live Reviews */}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "1.25rem",
                height: "calc(100vh - 160px)",
                minHeight: "650px",
                overflowY: "auto",
                paddingRight: "0.25rem",
              }}
            >
              {selectedFilm ? (
                <>
                  {/* Selected Film Spotlight Banner */}
                  <div
                    style={{
                      backgroundColor: "rgba(15, 23, 42, 0.8)",
                      border: "1px solid rgba(255, 255, 255, 0.08)",
                      borderRadius: "16px",
                      padding: "1.5rem",
                      background: "linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.95) 100%)",
                      boxShadow: "0 8px 32px rgba(0, 0, 0, 0.25)",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                          <span
                            style={{
                              fontSize: "0.7rem",
                              fontWeight: "700",
                              padding: "0.15rem 0.5rem",
                              borderRadius: "4px",
                              backgroundColor: "rgba(99, 102, 241, 0.2)",
                              color: "#a5b4fc",
                              textTransform: "uppercase",
                              letterSpacing: "0.05em",
                            }}
                          >
                            {selectedFilm.genre}
                          </span>
                          <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                            Released {selectedFilm.releaseYear} • Directed by {selectedFilm.director}
                          </span>
                        </div>
                        <h1 style={{ fontSize: "1.75rem", fontWeight: "800", marginTop: "0.35rem", letterSpacing: "-0.02em" }}>
                          {selectedFilm.title}
                        </h1>
                        <div style={{ fontSize: "0.75rem", color: "#64748b", fontFamily: "'JetBrains Mono', monospace", marginTop: "0.2rem" }}>
                          Film ID: {selectedFilm.id}
                        </div>
                      </div>

                      {/* Stat Counters updated by BackgroundTask */}
                      <div style={{ display: "flex", gap: "0.75rem" }}>
                        <div
                          style={{
                            backgroundColor: "rgba(7, 11, 20, 0.6)",
                            border: "1px solid rgba(245, 158, 11, 0.3)",
                            borderRadius: "12px",
                            padding: "0.65rem 1rem",
                            textAlign: "center",
                            minWidth: "110px",
                          }}
                        >
                          <div style={{ fontSize: "0.7rem", color: "#fbbf24", fontWeight: "700", textTransform: "uppercase" }}>
                            Average Rating
                          </div>
                          <div style={{ fontSize: "1.4rem", fontWeight: "800", color: "#fef3c7", marginTop: "0.15rem" }}>
                            {selectedFilm.average_rating !== null && selectedFilm.average_rating !== undefined
                              ? `★ ${selectedFilm.average_rating}`
                              : "N/A"}
                          </div>
                        </div>

                        <div
                          style={{
                            backgroundColor: "rgba(7, 11, 20, 0.6)",
                            border: "1px solid rgba(99, 102, 241, 0.3)",
                            borderRadius: "12px",
                            padding: "0.65rem 1rem",
                            textAlign: "center",
                            minWidth: "110px",
                          }}
                        >
                          <div style={{ fontSize: "0.7rem", color: "#a5b4fc", fontWeight: "700", textTransform: "uppercase" }}>
                            Total Reviews
                          </div>
                          <div style={{ fontSize: "1.4rem", fontWeight: "800", color: "#e0e7ff", marginTop: "0.15rem" }}>
                            {selectedFilm.total_reviews ?? selectedFilm.review_count ?? 0}
                          </div>
                        </div>
                      </div>
                    </div>

                    {selectedFilm.description && (
                      <p style={{ fontSize: "0.85rem", color: "#94a3b8", lineHeight: "1.5", marginTop: "1rem" }}>
                        {selectedFilm.description}
                      </p>
                    )}
                  </div>

                  {/* Review Submission Form Card */}
                  <div
                    style={{
                      backgroundColor: "rgba(15, 23, 42, 0.75)",
                      border: "1px solid rgba(255, 255, 255, 0.08)",
                      borderRadius: "16px",
                      padding: "1.25rem 1.5rem",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.85rem" }}>
                      <div>
                        <h3 style={{ fontSize: "1rem", fontWeight: "700" }}>Submit a Verified Review</h3>
                        <p style={{ fontSize: "0.75rem", color: "#64748b" }}>
                          Returns HTTP 201 immediately; triggers async background worker to recompute film statistics.
                        </p>
                      </div>
                      <span
                        style={{
                          fontSize: "0.7rem",
                          fontWeight: "600",
                          backgroundColor: "rgba(16, 185, 129, 0.1)",
                          color: "#34d399",
                          padding: "0.2rem 0.5rem",
                          borderRadius: "9999px",
                          border: "1px solid rgba(16, 185, 129, 0.2)",
                        }}
                      >
                        ⚡ BackgroundTasks Active
                      </span>
                    </div>

                    <form onSubmit={handleReviewSubmit} style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
                      <div style={{ display: "grid", gridTemplateColumns: "180px 1fr", gap: "1rem" }}>
                        {/* Rating Manual Input (1 - 10) */}
                        <div>
                          <label style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600", display: "block", marginBottom: "0.3rem" }}>
                            Rating (1 – 10)
                          </label>
                          <div style={{ position: "relative" }}>
                            <input
                              type="number"
                              min={1}
                              max={10}
                              step={1}
                              value={rating}
                              onChange={(e) => setRating(e.target.value)}
                              placeholder="1 – 10"
                              style={{
                                width: "100%",
                                padding: "0.5rem 0.75rem",
                                paddingRight: "2rem",
                                borderRadius: "8px",
                                backgroundColor: "rgba(7, 11, 20, 0.7)",
                                border: "1px solid rgba(255, 255, 255, 0.12)",
                                color: "#fbbf24",
                                fontWeight: "700",
                                fontSize: "0.85rem",
                              }}
                            />
                            <span
                              style={{
                                position: "absolute",
                                right: "0.75rem",
                                top: "50%",
                                transform: "translateY(-50%)",
                                color: "#fbbf24",
                                fontSize: "0.85rem",
                                pointerEvents: "none",
                              }}
                            >
                              ★
                            </span>
                          </div>
                        </div>

                        {/* Reviewer Display Name */}
                        <div>
                          <label style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600", display: "block", marginBottom: "0.3rem" }}>
                            Reviewer Display Name
                          </label>
                          <input
                            type="text"
                            value={reviewerDisplayName}
                            placeholder={userProfile?.username || "Critic Name"}
                            onChange={(e) => setReviewerDisplayName(e.target.value)}
                            style={{
                              width: "100%",
                              padding: "0.5rem 0.75rem",
                              borderRadius: "8px",
                              backgroundColor: "rgba(7, 11, 20, 0.7)",
                              border: "1px solid rgba(255, 255, 255, 0.12)",
                              color: "#f8fafc",
                              fontSize: "0.85rem",
                            }}
                          />
                        </div>
                      </div>

                      {/* Review Text */}
                      <div>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.3rem" }}>
                          <label style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>
                            Review Text (Minimum 50 characters)
                          </label>
                          <span
                            style={{
                              fontSize: "0.72rem",
                              fontWeight: "700",
                              color: reviewComment.trim().length >= 50 ? "#34d399" : "#f59e0b",
                            }}
                          >
                            {reviewComment.trim().length} / 50 characters
                          </span>
                        </div>
                        <textarea
                          rows={3}
                          value={reviewComment}
                          onChange={(e) => setReviewComment(e.target.value)}
                          placeholder="Provide an in-depth cinematic critique (minimum 50 characters required by schema)..."
                          style={{
                            width: "100%",
                            padding: "0.6rem 0.75rem",
                            borderRadius: "8px",
                            backgroundColor: "rgba(7, 11, 20, 0.7)",
                            border:
                              reviewComment.trim().length > 0 && reviewComment.trim().length < 50
                                ? "1px solid rgba(245, 158, 11, 0.4)"
                                : "1px solid rgba(255, 255, 255, 0.12)",
                            color: "#f8fafc",
                            fontSize: "0.85rem",
                            resize: "vertical",
                            lineHeight: "1.4",
                          }}
                        />
                      </div>

                      {/* Form Actions */}
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "0.25rem" }}>
                        <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                          Submitting as:{" "}
                          <strong style={{ color: "#38bdf8" }}>
                            {userProfile ? `${userProfile.username} (${userProfile.role})` : "Unauthenticated"}
                          </strong>
                        </span>

                        <button
                          type="submit"
                          disabled={submittingReview || !userProfile}
                          style={{
                            background: "linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)",
                            color: "#ffffff",
                            border: "none",
                            padding: "0.6rem 1.4rem",
                            borderRadius: "8px",
                            fontSize: "0.85rem",
                            fontWeight: "600",
                            cursor: userProfile ? "pointer" : "not-allowed",
                            opacity: userProfile ? 1 : 0.6,
                            boxShadow: "0 4px 14px rgba(99, 102, 241, 0.35)",
                            transition: "all 0.15s ease",
                          }}
                        >
                          {submittingReview ? "Posting Review..." : "Submit Review →"}
                        </button>
                      </div>
                    </form>

                    {/* Feedback Toast */}
                    {reviewFeedback && (
                      <div
                        style={{
                          marginTop: "0.85rem",
                          padding: "0.65rem 0.9rem",
                          borderRadius: "8px",
                          fontSize: "0.8rem",
                          lineHeight: "1.4",
                          backgroundColor:
                            reviewFeedback.type === "error"
                              ? "rgba(239, 68, 68, 0.15)"
                              : reviewFeedback.type === "success"
                              ? "rgba(16, 185, 129, 0.15)"
                              : "rgba(56, 189, 248, 0.15)",
                          border:
                            reviewFeedback.type === "error"
                              ? "1px solid rgba(239, 68, 68, 0.35)"
                              : reviewFeedback.type === "success"
                              ? "1px solid rgba(16, 185, 129, 0.35)"
                              : "1px solid rgba(56, 189, 248, 0.35)",
                          color:
                            reviewFeedback.type === "error"
                              ? "#fca5a5"
                              : reviewFeedback.type === "success"
                              ? "#6ee7b7"
                              : "#7dd3fc",
                        }}
                      >
                        {reviewFeedback.message}
                      </div>
                    )}
                  </div>

                  {/* Reviews Feed for Selected Film */}
                  <div
                    style={{
                      backgroundColor: "rgba(15, 23, 42, 0.75)",
                      border: "1px solid rgba(255, 255, 255, 0.08)",
                      borderRadius: "16px",
                      padding: "1.25rem 1.5rem",
                      display: "flex",
                      flexDirection: "column",
                      gap: "0.75rem",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <h3 style={{ fontSize: "0.95rem", fontWeight: "700" }}>
                        Verified Critic Reviews for {selectedFilm.title}
                      </h3>
                      <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                        {filmReviews.length} {filmReviews.length === 1 ? "entry" : "entries"}
                      </span>
                    </div>

                    {reviewsLoading ? (
                      <div style={{ fontSize: "0.8rem", color: "#64748b", padding: "1rem 0" }}>
                        Loading reviews from route...
                      </div>
                    ) : filmReviews.length === 0 ? (
                      <div
                        style={{
                          fontSize: "0.8rem",
                          color: "#64748b",
                          padding: "1.5rem 0",
                          textAlign: "center",
                          backgroundColor: "rgba(7, 11, 20, 0.4)",
                          borderRadius: "8px",
                        }}
                      >
                        No reviews yet for {selectedFilm.title}. Submit the first critique above!
                      </div>
                    ) : (
                      <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                        {filmReviews.map((rev) => (
                          <div
                            key={rev.id}
                            style={{
                              backgroundColor: "rgba(11, 16, 29, 0.6)",
                              border: "1px solid rgba(255, 255, 255, 0.05)",
                              borderRadius: "10px",
                              padding: "0.85rem 1rem",
                            }}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.35rem" }}>
                              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                                <div
                                  style={{
                                    width: "24px",
                                    height: "24px",
                                    borderRadius: "50%",
                                    backgroundColor: "rgba(99, 102, 241, 0.2)",
                                    color: "#a5b4fc",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    fontSize: "0.7rem",
                                    fontWeight: "700",
                                  }}
                                >
                                  {rev.reviewer_display_name ? rev.reviewer_display_name[0].toUpperCase() : "U"}
                                </div>
                                <span style={{ fontSize: "0.85rem", fontWeight: "600", color: "#f8fafc" }}>
                                  {rev.reviewer_display_name || "Critic"}
                                </span>
                              </div>

                              <span
                                style={{
                                  fontSize: "0.75rem",
                                  color: "#fbbf24",
                                  fontWeight: "700",
                                  backgroundColor: "rgba(245, 158, 11, 0.12)",
                                  padding: "0.15rem 0.5rem",
                                  borderRadius: "6px",
                                  border: "1px solid rgba(245, 158, 11, 0.25)",
                                }}
                              >
                                ★ {rev.rating} / 10
                              </span>
                            </div>
                            <p style={{ fontSize: "0.8rem", color: "#94a3b8", lineHeight: "1.45" }}>
                              {rev.review}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div
                  style={{
                    backgroundColor: "rgba(15, 23, 42, 0.6)",
                    border: "1px dashed rgba(255, 255, 255, 0.1)",
                    borderRadius: "16px",
                    padding: "3rem",
                    textAlign: "center",
                    color: "#64748b",
                  }}
                >
                  Select a film from the catalogue to view details, submit reviews, and view statistics.
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
