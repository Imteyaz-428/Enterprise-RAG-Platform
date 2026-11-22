import api from "./api";
import { getToken } from "../utils/token";
import { createSSEParser, parseEventBlock } from "../utils/sse";

export { createSSEParser, parseEventBlock };

const BASE_URL = import.meta.env.VITE_API_URL || "";

export const getSessions = async () => {
  const res = await api.get("/chat/sessions");
  return res.data;
};

export const getSession = async (sessionId) => {
  const res = await api.get(`/chat/sessions/${sessionId}`);
  return res.data;
};

export const deleteSession = async (sessionId) => {
  const res = await api.delete(`/chat/sessions/${sessionId}`);
  return res.data;
};

export const streamChat = async ({
  question,
  sessionId,
  onMetadata,
  onToken,
  onDone,
  onError,
}) => {
  try {
    const token = getToken();

    const response = await fetch(`${BASE_URL}/chat/stream`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question,
        session_id: sessionId,
      }),
    });

    if (!response.ok) {
      let errorMsg = "Failed to start chat.";
      try {
        const errorData = await response.json();
        if (errorData?.detail) {
          errorMsg = errorData.detail;
        } else if (errorData?.error) {
          errorMsg = errorData.error;
        }
      } catch {
        errorMsg = response.statusText || errorMsg;
      }
      throw new Error(errorMsg);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    const parser = createSSEParser((event) => {
      const { type, data } = event;

      switch (type) {
        case "metadata": {
          try {
            const parsed = JSON.parse(data);
            onMetadata?.(parsed);
          } catch (err) {
            console.error("Failed to parse metadata:", err);
          }
          break;
        }

        case "token":
          onToken?.(data);
          break;

        case "done":
          onDone?.();
          break;

        case "error": {
          let errorText = data;
          try {
            const parsed = JSON.parse(data);
            if (parsed && typeof parsed === "object" && parsed.error) {
              errorText = parsed.error;
            } else if (typeof parsed === "string") {
              errorText = parsed;
            }
          } catch {
            // Keep plain text
          }
          onError?.(new Error(errorText));
          break;
        }

        default:
          console.log("Unknown SSE Event:", type);
      }
    });

    while (true) {
      const { value, done } = await reader.read();

      if (done) {
        break;
      }

      const chunk = decoder.decode(value, { stream: true });
      parser.feed(chunk);
    }
  } catch (err) {
    console.error(err);
    onError?.(err);
  }
};
