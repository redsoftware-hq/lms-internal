/*
 * QA LMS UI enhancements — runtime DOM patches for the upstream LMS Vue SPA.
 *
 * Injected via lms_internal/brand.py (after_request). Uses a MutationObserver
 * on document.body — the same proven pattern as profile_fields.js — to modify
 * upstream-rendered DOM without forking the LMS frontend.
 *
 * Concern (ported from the parent quality-asia-lms, trimmed to the internal LMS):
 *   - Replace the confusing "0 out of 0" quiz summary for ungraded quizzes
 *     (the per-course feedback surveys) with a friendly confirmation message.
 */
(function () {
	"use strict";
	if (window.__qaLmsUI) return;
	window.__qaLmsUI = true;

	var FEEDBACK_MESSAGE = "Thank you! Your responses have been recorded successfully.";

	// The upstream Quiz Summary score line (Quiz.vue):
	//   "You got {pct}% correct answers with a score of {score} out of {out_of}"
	// An ungraded feedback quiz has out_of === 0. Match the string itself rather
	// than the surrounding CSS classes so this survives LMS frontend re-skins.
	var SCORE_RE = /correct answers with a score of\s+-?\d+\s+out of\s+(\d+)/i;

	/* ------------------------------------------------------------------ */
	/* Friendly quiz summary for ungraded (feedback) quizzes              */
	/* ------------------------------------------------------------------ */

	function fixQuizSummary() {
		// The score sits in a leaf <div> whose own text is the score sentence.
		var nodes = document.querySelectorAll("div");
		for (var i = 0; i < nodes.length; i++) {
			var el = nodes[i];
			if (el.children.length !== 0) continue; // leaf text node only
			if (el.dataset.qaFeedback === "1") continue;

			var text = (el.textContent || "").trim();
			var m = text.match(SCORE_RE);
			if (!m || m[1] !== "0") continue; // only ungraded (out of 0) surveys

			el.dataset.qaFeedback = "1";
			// Hide the stock "0 out of 0" line, insert a friendly QA-owned sibling
			// (a new node, not a mutation of Vue-managed text, so re-renders can't
			// clobber it).
			el.style.display = "none";
			var msg = document.createElement("div");
			msg.className = el.className;
			msg.setAttribute("data-qa", "feedback-thanks");
			msg.textContent = FEEDBACK_MESSAGE;
			el.parentNode.insertBefore(msg, el.nextSibling);
			return;
		}
	}

	/* ------------------------------------------------------------------ */
	/* Observer — watch the SPA for the rendered quiz summary             */
	/* ------------------------------------------------------------------ */

	var observer = new MutationObserver(function () {
		try {
			fixQuizSummary();
		} catch (e) {
			/* fail-safe: never break the stock pages */
		}
	});
	observer.observe(document.body, { childList: true, subtree: true });

	// Also run once immediately for content already rendered
	try {
		fixQuizSummary();
	} catch (e) {
		/* fail-safe */
	}
})();
