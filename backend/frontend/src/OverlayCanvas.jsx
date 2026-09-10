/**
 * Renders masks and bounding boxes over the source image
 *
 * OWNER: P5
 * STATUS: placeholder created by P1 on 31 Aug. P5 replaces this file.
 *
 * Build against P4's mock endpoint from day one -- never wait for a real model.
 * Response shape: docs/api_contract_request.md
 *
 * Two things P1 would ask for specifically:
 *
 * 1. Render intent "unclear" as a normal answer, not an error state. The router
 *    asks a clarifying question when it is not confident, and that is a feature
 *    we demo on purpose.
 *
 * 2. A small "show computed values" toggle that reveals the raw `computed`
 *    object beside the sentence. Thirty minutes of work, and it turns the
 *    project's main claim -- numbers computed, language generated -- into
 *    something a judge can watch instead of something we assert.
 *
 * Design for a projector: large text, high contrast, no small grey type.
 */

export default function Placeholder() {
  return null;
}
