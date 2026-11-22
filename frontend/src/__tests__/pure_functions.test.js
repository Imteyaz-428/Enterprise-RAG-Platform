import { describe, it, expect } from "vitest";
import { createSSEParser, parseEventBlock } from "../utils/sse";
import {
  extractCitationMarkers,
  isNotFound,
  getDisplayedCitations,
  formatCitationMarkdown,
  NOT_FOUND_SENTENCE,
} from "../utils/citations";
import { hasRole, ROLE_HIERARCHY } from "../utils/roles";

describe("SSE Parser", () => {
  it("handles parseEventBlock for basic event and data", () => {
    const block = "event: token\ndata: hello";
    const parsed = parseEventBlock(block);
    expect(parsed).toEqual({ type: "token", data: "hello" });
  });

  it("handles split chunks across buffer feeds", () => {
    const events = [];
    const parser = createSSEParser((ev) => events.push(ev));

    parser.feed("event: to");
    expect(events.length).toBe(0);

    parser.feed("ken\ndata: chunked message\n\n");
    expect(events.length).toBe(1);
    expect(events[0]).toEqual({
      type: "token",
      data: "chunked message",
    });
  });

  it("removes EXACTLY ONE leading space from data: line (never trim)", () => {
    // 1 leading space -> removed
    const block1 = "event: token\ndata: hello";
    expect(parseEventBlock(block1).data).toBe("hello");

    // 2 leading spaces -> only 1 removed, preserves 1 space
    const block2 = "event: token\ndata:  hello with space";
    expect(parseEventBlock(block2).data).toBe(" hello with space");

    // 3 leading spaces -> only 1 removed, preserves 2 spaces
    const block3 = "event: token\ndata:   three spaces";
    expect(parseEventBlock(block3).data).toBe("  three spaces");

    // No leading space after data:
    const block4 = "event: token\ndata:nospace";
    expect(parseEventBlock(block4).data).toBe("nospace");
  });

  it("handles newline tokens correctly byte-for-byte", () => {
    // Backend formats "\n" as two data lines with empty pieces:
    // data: 
    // data: 
    const block = "event: token\ndata: \ndata: ";
    const parsed = parseEventBlock(block);
    expect(parsed).toEqual({ type: "token", data: "\n" });
  });

  it("joins multiple data lines with \\n", () => {
    const block = "event: token\ndata: first line\ndata: second line\ndata: third line";
    const parsed = parseEventBlock(block);
    expect(parsed).toEqual({
      type: "token",
      data: "first line\nsecond line\nthird line",
    });
  });

  it("accepts CRLF (\\r\\n and \\r\\n\\r\\n) event delimiters", () => {
    const events = [];
    const parser = createSSEParser((ev) => events.push(ev));

    parser.feed("event: token\r\ndata: windows newline\r\n\r\nevent: token\r\ndata: second\r\n\r\n");
    expect(events.length).toBe(2);
    expect(events[0]).toEqual({ type: "token", data: "windows newline" });
    expect(events[1]).toEqual({ type: "token", data: "second" });
  });

  it("handles error events with JSON and plain text payloads", () => {
    const events = [];
    const parser = createSSEParser((ev) => events.push(ev));

    const jsonErrorPayload = JSON.stringify({
      error: "AI provider generation failed. Please try again later.",
    });

    parser.feed(`event: error\ndata: ${jsonErrorPayload}\n\n`);
    parser.feed("event: error\ndata: Plain text error message\n\n");

    expect(events.length).toBe(2);
    expect(events[0].type).toBe("error");
    expect(JSON.parse(events[0].data)).toEqual({
      error: "AI provider generation failed. Please try again later.",
    });
    expect(events[1]).toEqual({
      type: "error",
      data: "Plain text error message",
    });
  });

  it("handles metadata and done events", () => {
    const events = [];
    const parser = createSSEParser((ev) => events.push(ev));

    const meta = JSON.stringify({
      session_id: 123,
      citations: [{ id: 1, document: "test.pdf", page_number: 2 }],
    });

    parser.feed(`event: metadata\ndata: ${meta}\n\nevent: done\ndata: {}\n\n`);
    expect(events.length).toBe(2);
    expect(events[0].type).toBe("metadata");
    expect(JSON.parse(events[0].data).session_id).toBe(123);
    expect(events[1].type).toBe("done");
  });
});

describe("Citation and Marker Parser", () => {
  it("parses single, adjacent, and spaced [n] markers into integer IDs", () => {
    const text = "Found in [1], adjacent [1][2], and spaced [ 3 ] as well as [  4  ].";
    const markers = extractCitationMarkers(text);
    expect(markers).toEqual([1, 1, 2, 3, 4]);
  });

  it("returns empty array when text has no markers or is empty", () => {
    expect(extractCitationMarkers("No citations here")).toEqual([]);
    expect(extractCitationMarkers("")).toEqual([]);
    expect(extractCitationMarkers(null)).toEqual([]);
  });

  it("identifies not-found sentences correctly", () => {
    expect(isNotFound(NOT_FOUND_SENTENCE)).toBe(true);
    expect(
      isNotFound(
        "I could not find this in the provided documents. Please try another query."
      )
    ).toBe(true);
    expect(isNotFound("Here is the answer based on documents.")).toBe(false);
    expect(isNotFound("")).toBe(false);
    expect(isNotFound(null)).toBe(false);
  });

  it("getDisplayedCitations suppresses sources on not-found sentence", () => {
    const citations = [
      { id: 1, document: "doc1.pdf" },
      { id: 2, document: "doc2.pdf" },
    ];
    const result = getDisplayedCitations(
      "I could not find this in the provided documents.",
      citations
    );
    expect(result).toEqual([]);
  });

  it("getDisplayedCitations filters citations to only those whose id appears in the text", () => {
    const citations = [
      { id: 1, document: "doc1.pdf" },
      { id: 2, document: "doc2.pdf" },
      { id: 3, document: "doc3.pdf" },
    ];
    const text = "According to [1] and [ 3 ], the system works.";
    const result = getDisplayedCitations(text, citations);
    expect(result).toEqual([
      { id: 1, document: "doc1.pdf" },
      { id: 3, document: "doc3.pdf" },
    ]);
  });

  it("getDisplayedCitations shows all citations if text has no markers and is not not-found", () => {
    const citations = [
      { id: 1, document: "doc1.pdf" },
      { id: 2, document: "doc2.pdf" },
    ];
    const text = "This answer has no explicit markers.";
    const result = getDisplayedCitations(text, citations);
    expect(result).toEqual(citations);
  });

  it("formatCitationMarkdown converts [n], [1][2], and [ 1 ] to internal links", () => {
    const text = "See [1], adjacent [1][2], and spaced [ 3 ].";
    const formatted = formatCitationMarkdown(text);
    expect(formatted).toBe(
      "See [1](#cite-1), adjacent [1](#cite-1)[2](#cite-2), and spaced [3](#cite-3)."
    );
  });

  it("formatCitationMarkdown suppresses link conversion on not-found sentence", () => {
    const text = `${NOT_FOUND_SENTENCE} [1]`;
    expect(formatCitationMarkdown(text)).toBe(text);
  });
});

describe("Roles (hasRole)", () => {
  it("enforces super_admin > admin > manager > employee hierarchy", () => {
    expect(ROLE_HIERARCHY.super_admin).toBeGreaterThan(ROLE_HIERARCHY.admin);
    expect(ROLE_HIERARCHY.admin).toBeGreaterThan(ROLE_HIERARCHY.manager);
    expect(ROLE_HIERARCHY.manager).toBeGreaterThan(ROLE_HIERARCHY.employee);
  });

  it("correctly evaluates super_admin permissions", () => {
    const superAdmin = { role: "super_admin" };
    expect(hasRole(superAdmin, "super_admin")).toBe(true);
    expect(hasRole(superAdmin, "admin")).toBe(true);
    expect(hasRole(superAdmin, "manager")).toBe(true);
    expect(hasRole(superAdmin, "employee")).toBe(true);
  });

  it("correctly evaluates admin permissions", () => {
    const admin = { role: "admin" };
    expect(hasRole(admin, "super_admin")).toBe(false);
    expect(hasRole(admin, "admin")).toBe(true);
    expect(hasRole(admin, "manager")).toBe(true);
    expect(hasRole(admin, "employee")).toBe(true);
  });

  it("correctly evaluates manager permissions", () => {
    const manager = { role: "manager" };
    expect(hasRole(manager, "super_admin")).toBe(false);
    expect(hasRole(manager, "admin")).toBe(false);
    expect(hasRole(manager, "manager")).toBe(true);
    expect(hasRole(manager, "employee")).toBe(true);
  });

  it("correctly evaluates employee permissions", () => {
    const employee = { role: "employee" };
    expect(hasRole(employee, "super_admin")).toBe(false);
    expect(hasRole(employee, "admin")).toBe(false);
    expect(hasRole(employee, "manager")).toBe(false);
    expect(hasRole(employee, "employee")).toBe(true);
  });

  it("handles string arguments and case-insensitivity", () => {
    expect(hasRole("ADMIN", "manager")).toBe(true);
    expect(hasRole("Manager", "ADMIN")).toBe(false);
    expect(hasRole({ role: "EMPLOYEE" }, "employee")).toBe(true);
  });

  it("returns false for invalid, missing, or unknown roles", () => {
    expect(hasRole(null, "employee")).toBe(false);
    expect(hasRole({}, "employee")).toBe(false);
    expect(hasRole({ role: "guest" }, "employee")).toBe(false);
    expect(hasRole("admin", "unknown_role")).toBe(false);
  });
});
