/*
 * QA LMS UI enhancements — runtime DOM patches for the upstream LMS Vue SPA.
 *
 * Injected via lms_internal/brand.py (after_request). Uses a MutationObserver
 * on document.body — the same proven pattern as profile_fields.js — to modify
 * upstream-rendered DOM without forking the LMS frontend.
 *
 * Concerns (ported from the parent quality-asia-lms, trimmed to the internal LMS):
 *   1. Replace the confusing "0 out of 0" quiz summary for ungraded quizzes
 *      (the per-course feedback surveys) with a friendly confirmation message.
 *   2. Rewrite the stock "Not Permitted" card with friendlier login-required copy.
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
	/* Friendly "Not Permitted" page text                                 */
	/*                                                                    */
	/* Rewrites the NotPermitted / NoPermission card. Per-node data flag   */
	/* (not a global latch) so Vue re-renders get re-patched.             */
	/* ------------------------------------------------------------------ */

	var NOT_PERMITTED_STRINGS = ["Not Permitted"];
	var BODY_STRINGS = [
		"You are not permitted to access this page.",
		"Please login to access this page.",
		"You do not have permission to access this page.",
	];

	function friendlyNotPermitted() {
		var headings = document.querySelectorAll("h1, h2, h3, div, span");
		for (var i = 0; i < headings.length; i++) {
			var el = headings[i];
			if (el.dataset.qaPatched === "1") continue;

			// Get only the direct text content (ignore child element text)
			var directText = "";
			for (var n = 0; n < el.childNodes.length; n++) {
				if (el.childNodes[n].nodeType === 3) {
					directText += el.childNodes[n].textContent;
				}
			}
			directText = directText.trim();

			var isTitle = false;
			for (var t = 0; t < NOT_PERMITTED_STRINGS.length; t++) {
				if (directText === NOT_PERMITTED_STRINGS[t]) {
					isTitle = true;
					break;
				}
			}
			if (!isTitle) continue;

			// Replace the title text node(s) — preserve child elements (red dot span)
			for (var c = 0; c < el.childNodes.length; c++) {
				if (el.childNodes[c].nodeType === 3 && el.childNodes[c].textContent.trim()) {
					el.childNodes[c].textContent = el.childNodes[c].textContent.replace("Not Permitted", "Login Required");
				}
			}
			el.dataset.qaPatched = "1";

			// Find and replace the body text in the parent container
			var container = el.closest("div.border, div.rounded-md") || el.parentElement;
			if (!container) continue;

			var children = container.querySelectorAll("p, div, span");
			for (var j = 0; j < children.length; j++) {
				var child = children[j];
				var ct = (child.textContent || "").trim();
				for (var b = 0; b < BODY_STRINGS.length; b++) {
					if (ct.indexOf(BODY_STRINGS[b]) !== -1) {
						child.textContent = "Please log in to continue.";
						child.dataset.qaPatched = "1";
						break;
					}
				}
			}
		}
	}

	/* ------------------------------------------------------------------ */
	/* Observer — single watcher for all concerns                         */
	/* ------------------------------------------------------------------ */

	function runAll() {
		fixQuizSummary();
		friendlyNotPermitted();
	}

	var observer = new MutationObserver(function () {
		try {
			runAll();
		} catch (e) {
			/* fail-safe: never break the stock pages */
		}
	});
	observer.observe(document.body, { childList: true, subtree: true });

	// Also run once immediately for content already rendered
	try {
		runAll();
	} catch (e) {
		/* fail-safe */
	}
})();
