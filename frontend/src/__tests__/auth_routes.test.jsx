import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AuthProvider from "../context/AuthContext";
import AppRoutes from "../routes/AppRoutes";
import * as authService from "../services/auth";
import * as dashboardService from "../services/dashboard";

vi.mock("../services/auth", () => ({
  me: vi.fn(),
  login: vi.fn(),
  signup: vi.fn(),
}));

vi.mock("../services/dashboard", () => ({
  getDashboardData: vi.fn(),
}));

describe("Auth Routes & ProtectedRoute with AuthProvider", () => {
  beforeEach(() => {
    globalThis.localStorage.clear();
    globalThis.document.body.childNodes = [];
    vi.clearAllMocks();
  });

  it("(i) an unauthenticated visit to a protected route redirects to the login route", async () => {
    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Sign in to continue to your workspace.")).toBeDefined();
    });
  });

  it("(ii) with a mocked /auth/me the protected page renders", async () => {
    globalThis.localStorage.setItem("access_token", "valid-jwt-token");

    const mockUser = {
      id: 1,
      name: "Jane Doe",
      email: "jane@example.com",
      role: "admin",
      organization: { id: 1, name: "Acme Corp" },
    };

    vi.spyOn(authService, "me").mockResolvedValue(mockUser);
    vi.spyOn(dashboardService, "getDashboardData").mockResolvedValue({
      documents: [],
      users: [],
      sessions: [],
      currentUser: mockUser,
    });

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Enterprise AI Dashboard")).toBeDefined();
    });
  });

  it("throws Error('useAuth must be used inside <AuthProvider>') when provider is missing", async () => {
    const { useAuth } = await import("../context/useAuth");
    function BadComponent() {
      useAuth();
      return null;
    }
    expect(() => {
      render(<BadComponent />);
    }).toThrow("useAuth must be used inside <AuthProvider>");
  });
});
