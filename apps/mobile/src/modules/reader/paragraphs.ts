/**
 * Public Reader Rev 1 — plain-paragraph splitter for DraftVersion.content.
 *
 * No markdown parsing this wave (recon confirmed no markdown-rendering
 * library exists anywhere in apps/mobile's dependencies): a blank line is
 * the only structural rule, matching the "content is a plain-text/
 * markdown-ish blob" description in the architecture doc.
 */
export function splitParagraphs(content: string): string[] {
  return content
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter((p) => p.length > 0);
}
