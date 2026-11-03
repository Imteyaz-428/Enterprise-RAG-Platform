import { Menu, Plus, X } from "lucide-react";

export function MobileChatBar({ onMenu, onNewChat }) {
  return (
    <div className="flex items-center justify-between border-b bg-white px-3 py-2 md:hidden">
      <button
        onClick={onMenu}
        className="rounded-lg p-2 text-gray-700 active:bg-gray-100"
        aria-label="Open chats"
      >
        <Menu size={22} />
      </button>

      <span className="text-sm font-semibold text-gray-800">AI Chat</span>

      <button
        onClick={onNewChat}
        className="rounded-lg p-2 text-blue-600 active:bg-blue-50"
        aria-label="New chat"
      >
        <Plus size={22} />
      </button>
    </div>
  );
}

export default function MobileChatDrawer({ open, onClose, children }) {
  return (
    <div
      className={`absolute inset-0 z-40 md:hidden ${
        open ? "pointer-events-auto" : "pointer-events-none"
      }`}
    >
      {/* Backdrop */}
      <div
        onClick={onClose}
        className={`absolute inset-0 bg-black/40 transition-opacity duration-200 ${
          open ? "opacity-100" : "opacity-0"
        }`}
      />

      {/* Panel */}
      <div
        className={`absolute left-0 top-0 h-full w-[80%] max-w-[300px] bg-gray-50 shadow-xl transition-transform duration-200 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <button
          onClick={onClose}
          className="absolute right-2 top-2 z-10 rounded-lg p-2 text-gray-500 active:bg-gray-200"
          aria-label="Close chats"
        >
          <X size={20} />
        </button>
        <div className="h-full pt-10">{children}</div>
      </div>
    </div>
  );
}