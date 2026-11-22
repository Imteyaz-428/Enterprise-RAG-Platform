import { useEffect, useRef, useState, useCallback } from "react";
import toast from "react-hot-toast";

import Layout from "../../components/layout/Layout";
import ChatSidebar from "../../components/chat/ChatSidebar";
import ChatWindow from "../../components/chat/ChatWindow";
import ChatInput from "../../components/chat/ChatInput";
import EmptyChat from "../../components/chat/EmptyChat";
import MobileChatDrawer, { MobileChatBar } from "../../components/chat/MobileChatDrawer";
import {
  streamChat,
  getSessions,
  getSession,
  deleteSession,
} from "../../services/chat";

function Chat() {
  const [sessions, setSessions] = useState([]);
  const [messages, setMessages] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const pendingCitations = useRef([]);

  const fetchSessions = useCallback(async () => {
    try {
      const data = await getSessions();
      setSessions(data);
    } catch {
      toast.error("Failed to load chat sessions.");
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    async function load() {
      try {
        const data = await getSessions();
        if (!ignore) {
          setSessions(data);
        }
      } catch {
        toast.error("Failed to load chat sessions.");
      }
    }
    load();
    return () => {
      ignore = true;
    };
  }, []);

  const loadSession = async (sessionId) => {
    try {
      const data = await getSession(sessionId);

      setCurrentSessionId(sessionId);
      setMessages(data.messages || []);
      setDrawerOpen(false);
    } catch {
      toast.error("Failed to load chat.");
    }
  };

  const handleNewChat = () => {
    setCurrentSessionId(null);
    setMessages([]);
  };

  const handleDelete = async (sessionId) => {
    if (!window.confirm("Delete this chat?")) {
      return;
    }

    try {
      await deleteSession(sessionId);

      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setMessages([]);
      }

      fetchSessions();
      toast.success("Chat deleted.");
    } catch {
      toast.error("Delete failed.");
    }
  };

  const handleSend = async (question) => {
    pendingCitations.current = [];

    const userMessage = {
      role: "user",
      content: question,
    };

    const aiMessage = {
      role: "assistant",
      content: "",
      citations: [],
      error: null,
    };

    setMessages((prev) => [...prev, userMessage, aiMessage]);
    setLoading(true);

    await streamChat({
      question,
      sessionId: currentSessionId,

      onMetadata: (data) => {
        if (data.session_id) {
          setCurrentSessionId(data.session_id);
        }
        pendingCitations.current = data.citations || [];
        setMessages((prev) => {
          const copy = [...prev];
          const last = copy.length - 1;
          if (last >= 0 && copy[last].role === "assistant") {
            copy[last] = {
              ...copy[last],
              citations: data.citations || [],
            };
          }
          return copy;
        });
      },

      onToken: (token) => {
        setMessages((prev) => {
          const copy = [...prev];
          const last = copy.length - 1;
          if (last >= 0) {
            copy[last] = {
              ...copy[last],
              content: (copy[last].content || "") + token,
            };
          }
          return copy;
        });
      },

      onDone: async () => {
        setMessages((prev) => {
          const copy = [...prev];
          const last = copy.length - 1;
          if (last >= 0 && copy[last].role === "assistant") {
            copy[last] = {
              ...copy[last],
              citations:
                pendingCitations.current.length > 0
                  ? pendingCitations.current
                  : copy[last].citations || [],
              error: null,
            };
          }
          return copy;
        });

        pendingCitations.current = [];
        setLoading(false);
        await fetchSessions();
      },

      onError: (err) => {
        console.error("Stream error in Chat.jsx:", err);
        const errorText =
          err?.message ||
          "AI service temporarily unavailable. Please try again.";

        setLoading(false);
        setMessages((prev) => {
          const copy = [...prev];
          const last = copy.length - 1;
          if (last >= 0 && copy[last].role === "assistant") {
            copy[last] = {
              ...copy[last],
              error: errorText,
              citations:
                pendingCitations.current.length > 0
                  ? pendingCitations.current
                  : copy[last].citations || [],
            };
          }
          return copy;
        });

        pendingCitations.current = [];
        toast.error(errorText);
      },
    });
  };

  const handleRetry = async (_failedMessage, index) => {
    const question =
      index > 0 && messages[index - 1]?.role === "user"
        ? messages[index - 1].content
        : [...messages].reverse().find((m) => m.role === "user")?.content || "";

    if (!question) return;

    // Reset the failed assistant message and stream again
    setMessages((prev) => {
      const copy = [...prev];
      const targetIndex = index != null ? index : copy.length - 1;
      if (targetIndex >= 0) {
        copy[targetIndex] = {
          ...copy[targetIndex],
          content: "",
          citations: [],
          error: null,
        };
      }
      return copy;
    });

    setLoading(true);

    await streamChat({
      question,
      sessionId: currentSessionId,

      onMetadata: (data) => {
        if (data.session_id) {
          setCurrentSessionId(data.session_id);
        }
        pendingCitations.current = data.citations || [];
        setMessages((prev) => {
          const copy = [...prev];
          const targetIndex = index != null ? index : copy.length - 1;
          if (targetIndex >= 0 && copy[targetIndex].role === "assistant") {
            copy[targetIndex] = {
              ...copy[targetIndex],
              citations: data.citations || [],
            };
          }
          return copy;
        });
      },

      onToken: (token) => {
        setMessages((prev) => {
          const copy = [...prev];
          const targetIndex = index != null ? index : copy.length - 1;
          if (targetIndex >= 0) {
            copy[targetIndex] = {
              ...copy[targetIndex],
              content: (copy[targetIndex].content || "") + token,
            };
          }
          return copy;
        });
      },

      onDone: async () => {
        setMessages((prev) => {
          const copy = [...prev];
          const targetIndex = index != null ? index : copy.length - 1;
          if (targetIndex >= 0 && copy[targetIndex].role === "assistant") {
            copy[targetIndex] = {
              ...copy[targetIndex],
              citations:
                pendingCitations.current.length > 0
                  ? pendingCitations.current
                  : copy[targetIndex].citations || [],
              error: null,
            };
          }
          return copy;
        });

        pendingCitations.current = [];
        setLoading(false);
        await fetchSessions();
      },

      onError: (err) => {
        console.error("Retry stream error in Chat.jsx:", err);
        const errorText =
          err?.message ||
          "AI service temporarily unavailable. Please try again.";

        setLoading(false);
        setMessages((prev) => {
          const copy = [...prev];
          const targetIndex = index != null ? index : copy.length - 1;
          if (targetIndex >= 0 && copy[targetIndex].role === "assistant") {
            copy[targetIndex] = {
              ...copy[targetIndex],
              error: errorText,
            };
          }
          return copy;
        });

        pendingCitations.current = [];
        toast.error(errorText);
      },
    });
  };

  return (
    <Layout>
      <div className="h-[calc(100dvh-96px)] overflow-hidden rounded-xl border bg-white shadow-sm md:h-[calc(100dvh-110px)] md:rounded-2xl">
        <div className="relative flex h-full">
          <div className="hidden w-[220px] shrink-0 border-r bg-gray-50 md:block">
            <ChatSidebar
              sessions={sessions}
              currentSessionId={currentSessionId}
              onSelect={loadSession}
              onDelete={handleDelete}
              onNewChat={handleNewChat}
            />
          </div>

          <MobileChatDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)}>
            <ChatSidebar
              sessions={sessions}
              currentSessionId={currentSessionId}
              onSelect={loadSession}
              onDelete={handleDelete}
              onNewChat={handleNewChat}
            />
          </MobileChatDrawer>

          <div className="flex min-h-0 min-w-0 flex-1 flex-col bg-white">
            <MobileChatBar
              onMenu={() => setDrawerOpen(true)}
              onNewChat={handleNewChat}
            />

            <div className="min-h-0 flex-1">
              {messages.length === 0 ? (
                <EmptyChat />
              ) : (
                <ChatWindow
                  messages={messages}
                  loading={loading}
                  onRetry={handleRetry}
                />
              )}
            </div>

            <ChatInput loading={loading} onSend={handleSend} />
          </div>
        </div>
      </div>
    </Layout>
  );
}

export default Chat;
