export const NOT_FOUND_SENTENCE = "I could not find this in the provided documents.";

/**
 * Checks if the text starts with the not-found sentence.
 *
 * @param {string} text
 * @returns {boolean}
 */
export function isNotFound(text) {
  if (!text || typeof text !== "string") return false;
  return text.trim().startsWith(NOT_FOUND_SENTENCE);
}

/**
 * Extracts all integer citation IDs matching [n], [1][2], [ 1 ], etc.
 *
 * @param {string} text
 * @returns {number[]} Array of citation IDs in order of appearance
 */
export function extractCitationMarkers(text) {
  if (!text || typeof text !== "string") return [];
  const regex = /\[\s*(\d+)\s*\]/g;
  const ids = [];
  let match;
  while ((match = regex.exec(text)) !== null) {
    ids.push(parseInt(match[1], 10));
  }
  return ids;
}

/**
 * Filters the citations list according to the prompt rules:
 * - If text starts with "I could not find this in the provided documents." -> return empty array
 * - If text has citation markers [n] -> return only citations whose id appears in text
 * - If text has NO markers and is not the not-found sentence -> return all citations
 *
 * @param {string} text
 * @param {Array} citations
 * @returns {Array}
 */
export function getDisplayedCitations(text, citations) {
  if (!citations || !Array.isArray(citations) || citations.length === 0) {
    return [];
  }
  if (isNotFound(text)) {
    return [];
  }

  const markerIds = extractCitationMarkers(text);
  if (markerIds.length > 0) {
    const markerSet = new Set(markerIds);
    return citations.filter((c, idx) => {
      if (c && c.id != null) {
        return markerSet.has(Number(c.id));
      }
      // Fallback for 1-based index if citation has no explicit id
      return markerSet.has(idx + 1);
    });
  }

  return citations;
}

/**
 * Replaces [n] markers in markdown text with internal links [#cite-n](#cite-n)
 * unless the text starts with the not-found sentence.
 *
 * @param {string} text
 * @returns {string}
 */
export function formatCitationMarkdown(text) {
  if (!text || typeof text !== "string") return "";
  if (isNotFound(text)) {
    return text;
  }
  // Replace [ 1 ], [1][2], [n] with standard markdown link
  return text.replace(/\[\s*(\d+)\s*\]/g, "[$1](#cite-$1)");
}
