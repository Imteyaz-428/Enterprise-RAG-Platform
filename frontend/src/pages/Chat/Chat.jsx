import { useEffect, useRef, useState } from "react";
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

  const fetchSessions = async () => {
    try {
      const data = await getSessions();
      setSessions(data);
    } catch {
      toast.error("Failed to load chat sessions.");
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const loadSession = async (sessionId) => {
    try {
      const data = await getSession(sessionId);

      setCurrentSessionId(sessionId);
      setMessages(data.messages);
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
    };

    setMessages((prev) => [...prev, userMessage, aiMessage]);

    setLoading(true);

    await streamChat({
        question,
        sessionId: currentSessionId,
      
        onMetadata: (data) => {
         
          
      
          setCurrentSessionId(data.session_id);
      
          pendingCitations.current = data.citations || [];
      
          
        },
      
        onToken: (token) => {
          setMessages((prev) => {
            const copy = [...prev];
            const last = copy.length - 1;
      
            copy[last] = {
              ...copy[last],
              content: copy[last].content + token,
            };
      
            return copy;
          });
        },
      
        onDone: async () => {
         
          console.log("Citations:", pendingCitations.current);
      
          setMessages((prev) => {
            const copy = [...prev];
            const last = copy.length - 1;
      
            copy[last] = {
              ...copy[last],
              citations: pendingCitations.current,
            };
      
           
            console.log(copy[last]);
      
            return copy;
          });
      
          pendingCitations.current = [];
      
          setLoading(false);
          await fetchSessions();
        },
      
        onError: (err) => {
          console.error(err);
      
          pendingCitations.current = [];
          setLoading(false);
      
          toast.error("Something went wrong.");
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
              <ChatWindow messages={messages} loading={loading} />
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