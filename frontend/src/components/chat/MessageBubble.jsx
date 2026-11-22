import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { X, FileText, AlertCircle, RefreshCw } from "lucide-react";

import CitationList from "./CitationList";
import {
  isNotFound,
  formatCitationMarkdown,
  getDisplayedCitations,
} from "../../utils/citations";

function MessageBubble({ message, onRetry }) {
  const [activeCitation, setActiveCitation] = useState(null);
  const isUser = message.role === "user";
  const notFound = isNotFound(message.content);

  // Markdown safe formatting for citations
  const displayContent = !isUser && !notFound
    ? formatCitationMarkdown(message.content)
    : message.content;

  const displayedCitations = !isUser
    ? getDisplayedCitations(message.content, message.citations)
    : [];

  return (
    <div
      className={`flex mb-6 ${
        isUser ? "justify-end" : "justify-start"
      }`}
    >
      <div
        className={`max-w-[75%] rounded-2xl px-5 py-4 ${
          isUser
            ? "bg-blue-600 text-white rounded-br-md"
            : "bg-white border border-gray-200 shadow-sm rounded-bl-md"
        }`}
      >
        <p
          className={`mb-3 text-xs font-semibold ${
            isUser ? "text-blue-100" : "text-gray-500"
          }`}
        >
          {isUser ? "You" : "AI Assistant"}
        </p>

        {displayContent && (
          <div
            className={`prose prose-sm max-w-none leading-7 ${
              isUser
                ? "prose-invert text-white"
                : "text-gray-800"
            }`}
          >
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                a: ({ href, children, ...props }) => {
                  if (href && href.startsWith("#cite-")) {
                    const idStr = href.replace("#cite-", "");
                    const citeId = parseInt(idStr, 10);
                    const matchedCitation = message.citations?.find(
                      (c, idx) =>
                        (c && c.id != null
                          ? Number(c.id) === citeId
                          : idx + 1 === citeId)
                    );

                    return (
                      <button
                        type="button"
                        onClick={() =>
                          setActiveCitation(
                            matchedCitation || {
                              id: citeId,
                              document: `Source [${idStr}]`,
                            }
                          )
                        }
                        className="inline-flex items-center px-1.5 py-0.5 mx-0.5 text-xs font-semibold rounded bg-blue-100 text-blue-700 hover:bg-blue-200 transition-colors align-baseline cursor-pointer"
                        title={
                          matchedCitation
                            ? `${matchedCitation.document}${
                                matchedCitation.page_number
                                  ? ` (p. ${matchedCitation.page_number})`
                                  : ""
                              }`
                            : `Source [${idStr}]`
                        }
                      >
                        [{idStr}]
                      </button>
                    );
                  }

                  return (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      {...props}
                    >
                      {children}
                    </a>
                  );
                },
              }}
            >
              {displayContent}
            </ReactMarkdown>
          </div>
        )}

        {/* Error inside assistant bubble with Retry button */}
        {!isUser && message.error && (
          <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <AlertCircle size={18} className="text-red-500 shrink-0" />
              <span>{message.error}</span>
            </div>
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="flex items-center gap-1 shrink-0 rounded-lg bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700 transition shadow-sm"
              >
                <RefreshCw size={13} />
                Retry
              </button>
            )}
          </div>
        )}

        {/* Sources list */}
        {!isUser && !notFound && (
          <CitationList
            citations={displayedCitations}
            onSelectCitation={setActiveCitation}
          />
        )}
      </div>

      {/* Popover / Drawer for Citation Details */}
      {activeCitation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-start justify-between gap-4 border-b pb-4">
              <div className="flex items-center gap-3 min-w-0">
                <div className="rounded-lg bg-blue-50 p-2 text-blue-600 shrink-0">
                  <FileText size={20} />
                </div>
                <div className="min-w-0">
                  <h3 className="font-semibold text-gray-900 truncate">
                    {activeCitation.document || "Citation"}
                  </h3>
                  <div className="flex items-center gap-2 text-xs text-gray-500 mt-0.5">
                    {activeCitation.page_number != null && (
                      <span>Page {activeCitation.page_number}</span>
                    )}
                    {activeCitation.page_number != null && activeCitation.chunk_index != null && (
                      <span>•</span>
                    )}
                    {activeCitation.chunk_index != null && (
                      <span>Chunk {activeCitation.chunk_index}</span>
                    )}
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={() => setActiveCitation(null)}
                className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700 transition"
              >
                <X size={20} />
              </button>
            </div>

            <div className="mt-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">
                Snippet
              </p>
              {activeCitation.snippet ? (
                <div className="max-h-60 overflow-y-auto rounded-xl bg-gray-50 p-4 text-sm leading-relaxed text-gray-700 border">
                  <p className="whitespace-pre-wrap">{activeCitation.snippet}</p>
                </div>
              ) : (
                <p className="text-sm italic text-gray-400">
                  No text snippet available for this chunk.
                </p>
              )}
            </div>

            <div className="mt-6 flex justify-end">
              <button
                type="button"
                onClick={() => setActiveCitation(null)}
                className="rounded-xl bg-gray-100 px-5 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default MessageBubble;
