import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";

// Lightweight DOM shim so @testing-library/react works in vitest without external DOM packages
class MockNode {
  constructor(nodeType, nodeName) {
    this.nodeType = nodeType;
    this.nodeName = nodeName;
    this.childNodes = [];
    this.parentNode = null;
    this.ownerDocument = null;
  }
  get textContent() {
    if (this.nodeType === 3) return this.nodeValue || "";
    return this.childNodes.map((c) => c.textContent || "").join("");
  }
  set textContent(val) {
    this.childNodes = [];
    this.appendChild(globalThis.document.createTextNode(val));
  }
  appendChild(child) {
    this.childNodes.push(child);
    child.parentNode = this;
    child.ownerDocument = this.ownerDocument || this;
    return child;
  }
  removeChild(child) {
    const idx = this.childNodes.indexOf(child);
    if (idx !== -1) this.childNodes.splice(idx, 1);
    child.parentNode = null;
    return child;
  }
  insertBefore(newNode, refNode) {
    const idx = this.childNodes.indexOf(refNode);
    if (idx === -1) return this.appendChild(newNode);
    this.childNodes.splice(idx, 0, newNode);
    newNode.parentNode = this;
    newNode.ownerDocument = this.ownerDocument || this;
    return newNode;
  }
  contains(child) {
    if (child === this) return true;
    for (const c of this.childNodes) {
      if (c.contains && c.contains(child)) return true;
    }
    return false;
  }
}

class MockElement extends MockNode {
  constructor(name) {
    super(1, name.toUpperCase());
    this.tagName = name.toUpperCase();
    this.namespaceURI = "http://www.w3.org/1999/xhtml";
    this.attributes = {};
    this.style = {};
  }
  setAttribute(k, v) {
    this.attributes[k] = String(v);
  }
  getAttribute(k) {
    return this.attributes[k] || null;
  }
  removeAttribute(k) {
    delete this.attributes[k];
  }
  hasAttribute(k) {
    return k in this.attributes;
  }
  addEventListener() {}
  removeEventListener() {}
  dispatchEvent() {
    return true;
  }
  matches(sel) {
    if (sel === "*") return true;
    if (sel.toLowerCase() === this.tagName.toLowerCase()) return true;
    if (sel.startsWith("[") && sel.endsWith("]")) {
      const attr = sel.slice(1, -1);
      return attr in this.attributes;
    }
    return false;
  }
  querySelectorAll(sel) {
    const res = [];
    const check = (node) => {
      for (const c of node.childNodes) {
        if (c.nodeType === 1) {
          if (c.matches(sel)) res.push(c);
          check(c);
        }
      }
    };
    check(this);
    return res;
  }
  querySelector(sel) {
    return this.querySelectorAll(sel)[0] || null;
  }
}

class MockHTMLIFrameElement extends MockElement {}
class MockHTMLInputElement extends MockElement {}

class MockDocument extends MockNode {
  constructor() {
    super(9, "#document");
    this.body = new MockElement("body");
    this.body.ownerDocument = this;
    this.documentElement = new MockElement("html");
    this.documentElement.ownerDocument = this;
    this.activeElement = null;
    this.defaultView = globalThis;
  }
  createElement(tag) {
    const el = new MockElement(tag);
    el.ownerDocument = this;
    return el;
  }
  createComment() {
    return new MockNode(8, "#comment");
  }
  createTextNode(t) {
    const node = new MockNode(3, "#text");
    node.nodeValue = String(t);
    node.ownerDocument = this;
    return node;
  }
  querySelector(sel) {
    return this.body.querySelector(sel);
  }
  querySelectorAll(sel) {
    return this.body.querySelectorAll(sel);
  }
  addEventListener() {}
  removeEventListener() {}
}

if (!globalThis.document) {
  globalThis.Node = MockNode;
  globalThis.Element = MockElement;
  globalThis.HTMLIFrameElement = MockHTMLIFrameElement;
  globalThis.HTMLInputElement = MockHTMLInputElement;

  const mockDoc = new MockDocument();
  globalThis.document = mockDoc;
  globalThis.window = globalThis;
  globalThis.window.document = mockDoc;
  globalThis.window.addEventListener = () => {};
  globalThis.window.removeEventListener = () => {};
}

// LocalStorage mock
const storage = {};
globalThis.localStorage = {
  getItem: (k) => storage[k] || null,
  setItem: (k, v) => {
    storage[k] = String(v);
  },
  removeItem: (k) => {
    delete storage[k];
  },
  clear: () => {
    for (const k in storage) delete storage[k];
  },
};

// Now import RTL and router/components
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
    // Unauthenticated: no token in storage
    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    );

    // ProtectedRoute will redirect to /login
    await waitFor(() => {
      expect(screen.getByText("Sign in to continue to your workspace.")).toBeDefined();
    });
  });

  it("(ii) with a mocked /auth/me the protected page renders", async () => {
    // Authenticated: set access_token and mock me()
    globalThis.localStorage.setItem("access_token", "valid-jwt-token");

    const mockUser = {
      id: 1,
      name: "Jane Doe",
      email: "jane@example.com",
      role: "admin",
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

    // With authenticated user, dashboard renders
    await waitFor(() => {
      expect(screen.getByText("Enterprise AI Dashboard")).toBeDefined();
    });
  });

  it("throws Error('useAuth must be used inside <AuthProvider>') when provider is missing", () => {
    import("../context/useAuth").then(({ useAuth }) => {
      function BadComponent() {
        useAuth();
        return null;
      }
      expect(() => {
        render(<BadComponent />);
      }).toThrow("useAuth must be used inside <AuthProvider>");
    });
  });
});
