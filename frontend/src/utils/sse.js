/**
 * Parses a single SSE event block into type and data.
 * Per the SSE spec and prompt instructions:
 * - "event:" defines the event type
 * - For every "data:" line, remove EXACTLY ONE leading space (never trim)
 * - Join multiple "data:" lines with "\n"
 *
 * @param {string} block - Text block of one event
 * @returns {{ type: string, data: string }}
 */
export function parseEventBlock(block) {
  const lines = block.split(/\r?\n/);
  let type = "message";
  const dataLines = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      type = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      let content = line.slice(5);
      if (content.startsWith(" ")) {
        content = content.slice(1);
      }
      dataLines.push(content);
    }
  }

  const data = dataLines.join("\n");
  return { type, data };
}

/**
 * Creates an SSE parser that buffers partial reads and splits events on a blank line.
 * Accepts both \n\n and \r\n\r\n (and mixed \r?\n\r?\n).
 *
 * @param {Function} onEvent - Callback invoked for each complete event: ({ type, data }) => void
 * @returns {{ feed: (chunk: string) => void, reset: () => void, getBuffer: () => string }}
 */
export function createSSEParser(onEvent) {
  let buffer = "";

  function feed(chunk) {
    buffer += chunk;

    // Blank line is \r?\n\r?\n
    const parts = buffer.split(/\r?\n\r?\n/);

    // The last item is the remaining incomplete buffer
    buffer = parts.pop() || "";

    for (const part of parts) {
      if (!part.trim()) continue;
      const event = parseEventBlock(part);
      onEvent?.(event);
    }
  }

  function reset() {
    buffer = "";
  }

  function getBuffer() {
    return buffer;
  }

  return { feed, reset, getBuffer };
}
