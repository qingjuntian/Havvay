# Audiobook Service Plan

## Goal

Provide a book-oriented web service for turning a formatted DOCX and a voice sample into a reviewed, page-aligned F5-TTS audiobook video. Each stage has reviewable artifacts, an explicit user approval, and enough persisted state to resume after a process restart.

## Deployment

### AutoDL MVP

- Run the API, SQLite metadata database, Redis queue, and one background worker on the AutoDL instance.
- Keep the GPU worker concurrency at one. It owns F5-TTS inference and may also invoke the CPU-bound PDF/video tools.
- Run the API/video dependencies and F5-TTS in separate Python environments where their dependency constraints require it; the worker invokes F5 with the selected F5 interpreter.
- Store uploads and generated artifacts under a per-book directory on AutoDL's persistent data volume. Confirm the volume's lifecycle/retention semantics before production use.
- Serve the browser UI through the API. Start with authenticated, restricted access via SSH tunnel or the platform's controlled port forwarding; do not expose an unauthenticated service publicly.
- Use SQLite for book metadata, stage status, artifact versions, job state, and approval events. Redis/RQ is the execution queue, not the source of truth for workflow state.

### Growth Path

For multi-user or higher-availability use, move the API, database, and artifact storage to durable server/managed services. Keep AutoDL as a GPU worker that consumes queued jobs. Preserve the same job and artifact contracts when splitting the deployment.

## User Workflow

1. Create a book and upload the original formatted DOCX.
2. Convert DOCX to PDF, render page PNGs, extract page text, and show the page images for review.
3. Build a page-aligned TTS text file with `<<<BOOK_PAGE_BREAK>>>` between pages. Preserve raw extracted text separately from normalized text; show the normalized text for review and allow corrections.
4. Upload a voice sample and enter its exact `REF_TEXT`. Convert to mono 24 kHz, trim leading/trailing silence, enforce the F5 reference duration limit, then provide original and processed audio playback for review.
5. After approval, synthesize audio for the first five complete pages and show it for listening/review.
6. Render a video for those same five pages using their page images and measured chunk durations; show it for review.
7. After approval, synthesize the full audiobook and show it for review.
8. Render the full page-aligned video and show it for final review/download.

Every stage advances only after approval. Changing an upstream input invalidates approvals and outputs that depend on it. A preview limit is page-based, never an arbitrary chunk count.

## Text and Audio Rules

- Normalize Chinese-readable numbers for TTS (for example, `2012年` to `二零一二年` and `28岁` to `二十八岁`) while retaining the original extracted text for comparison and traceability.
- Treat dates, decimals, percentages, ranges, identifiers, and other number forms with explicit rules; do not blindly convert every digit sequence the same way.
- Preserve page boundaries and a mapping from normalized characters/chunks to source page numbers.
- Require the user's transcript to match the retained reference audio. Do not silently replace the supplied transcript with ASR output.
- Record synthesis settings and input hashes so unchanged F5 chunks can be reused safely.

## Persistence and Audit Trail

Per book, persist the original inputs, versioned intermediate/final artifacts, checksums, pipeline settings, job status/progress/logs/errors, and approval/rejection events with timestamps and user identity. Keep artifacts immutable by version instead of overwriting files in place. On restart, reconcile interrupted jobs from persisted state and allow retry from the last valid approved stage.

## Initial Data Model

- `books`: id, display name, current stage/status, timestamps.
- `artifacts`: book id, stage, version, kind, path, checksum, metadata, created timestamp.
- `jobs`: book id, stage, queue id, status, progress, timestamps, error summary.
- `events`: book id, stage, event type, actor, artifact version, note, timestamp.

## Implementation Phases

1. **Make the processing chain callable and testable.** Add the currently missing DOCX preparation entry point; wire number normalization into page extraction; retain raw and normalized page text; add a complete-page preview mode. The current `build_book_video.py` DOCX branch calls `src/prepare_docx.py`, but that file is absent. Its `--test-limit` is chunk-based and skips page timing/video, so it does not satisfy the five-page preview requirement.
2. **Add persistent service foundations.** Implement book/artifact/job/event records, upload and download endpoints, stage/status endpoints, approval gates, and restart-safe job tracking.
3. **Add the browser workflow.** Book list/detail, page image and text review, reference-audio review, preview audio/video, and final output review.
4. **Connect background stages.** Run DOCX processing, reference preparation, F5 preview/full synthesis, page timing, and video rendering via a single-concurrency worker. Make retries idempotent and reuse chunks only when relevant content and settings hashes match.
5. **Deploy and validate on AutoDL.** Configure persistent paths, GPU visibility, service supervision/restarts, restricted access, and backup/export. Exercise a short DOCX end to end, including edits, rejection, retry, and worker restart.
6. **Harden and scale.** Add authentication/authorization, upload limits and validation, cleanup/retention controls, operational monitoring, and optionally move the control plane and storage off AutoDL while keeping it as the GPU worker.

## Acceptance Checks

- Page image count, extracted page count, text page-break count, and page metadata agree.
- The text preview can be edited and the approved version is the exact text synthesized.
- Reference transcript and processed audio are independently reviewable before synthesis.
- Preview audio and video contain exactly the first five complete pages, except when the book has fewer than five.
- Full audio/video correspond to approved text, reference audio, and recorded settings.
- An interrupted job is visible after restart and can be retried without losing approved inputs or unrelated artifacts.
- Replacing a DOCX, text, or reference sample invalidates downstream approval and generated outputs.