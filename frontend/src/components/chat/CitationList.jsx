import { FileText } from "lucide-react";

function CitationList({ citations, onSelectCitation }) {
  if (!citations || !citations.length) {
    return null;
  }

  return (
    <div className="mt-4 border-t border-gray-200 pt-3">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
        Sources ({citations.length})
      </p>

      <div className="flex flex-col gap-2">
        {citations.map((citation, index) => {
          const docName = citation.document || `Document ${index + 1}`;
          const pageNum = citation.page_number;
          const chunkIdx = citation.chunk_index;

          return (
            <button
              type="button"
              key={citation.id ?? index}
              onClick={() => onSelectCitation?.(citation)}
              className="flex w-full items-center justify-between gap-2 rounded-lg bg-gray-50 px-3 py-2 text-left text-sm text-gray-700 transition hover:bg-gray-100 hover:text-blue-600"
            >
              <div className="flex items-center gap-2 min-w-0">
                <FileText size={16} className="text-gray-500 shrink-0" />

                <span className="truncate font-medium">
                  {docName}
                </span>

                {pageNum != null && (
                  <>
                    <span className="text-gray-400">•</span>
                    <span className="text-xs text-gray-500 shrink-0">
                      p. {pageNum}
                    </span>
                  </>
                )}

                {chunkIdx != null && (
                  <>
                    <span className="text-gray-400">•</span>
                    <span className="text-xs text-gray-500 shrink-0">
                      Chunk {chunkIdx}
                    </span>
                  </>
                )}
              </div>

              {citation.snippet && (
                <span className="text-xs text-blue-600 shrink-0 font-medium">
                  View
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default CitationList;
