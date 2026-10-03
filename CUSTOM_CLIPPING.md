# Hermes Video Clipper runbook

Every command below uses `hermes-video-clipper pipeline --workspace PATH` followed by the stage and arguments. On a source checkout, `node bin/cli.cjs` is equivalent to `hermes-video-clipper`.

## Stages

1. `intake "SOURCE_PATH_OR_URL" --rights user_reported --channel innovation`. Use confirmed only when genuinely established. Add `--source-url ORIGINAL_URL` for local files, optional `--campaign campaign.json` for supplied rules. The command returns the actual job path. Rights status does not establish platform reuse permission by itself.
2. `transcribe "JOB"`. CPU/int8 local faster-whisper small emits real word IDs/timestamps and EDITORIAL.md plus transcript pages. Reuse verified checkpoints; source/artifact changes reject stale timing.
3. Read full transcript context. Create candidates.json with reviewer, rank_order_confirmed:true and best-first clips containing safe lowercase id, name, topic, first_word_id, last_word_id, context_reviewed:true, optional warnings. All word references must exist. Use shortfall_reason when fewer than fifteen genuinely strong distinct moments exist.
4. `plan "JOB" "candidates.json"`. Only five enter production; ten extra ideas stay text-only. Direct `select "JOB" "selection.json"` is available for user-chosen extras/manual selections; extra selections use new intake --revision identities, never overwrite approved work.
5. `analyze "JOB"`. Saves actual camera-cut/face evidence and unreviewed framing.json. Inspect contact sheets/video; save reviewed:true, named reviewer and exactly one decision per shot: follow with track_id, split with two track_ids, or wide. Missing/unstable tracks reject composition. This is reviewed spatial association, not automatic active-speaker recognition.
6. `compose "JOB"` uses the user's music folder. Use explicit `--no-music` when there is no permitted music. `--music-id ID` chooses a saved bank track deliberately. Default gain 0.2; set track_volume_overrides in config by actual ID for exceptions. Videos supplied as music contribute audio only. Cached waveform/onset entries are heuristic and applied to music only. Speech stays unretimed.
7. `check "JOB"` performs actual browser/layout/runtime checks. Require JSON ok and browserSkipped:false; inspect warnings. Browser/model downloads require network on first setup, not paid APIs.
8. `render "JOB"` creates independent 1080x1920/30fps MP4s, SRTs and source/QA/music receipts. Uses strict delivery rendering, one worker and full decode. Hash-validated resume preserves prior outputs.
9. Play/inspect complete exports, then `approve "JOB" "CLIP_ID" --reviewer "NAME" --notes "REAL_CHECKS_AND_LIMITS"`. Until actual review, receipts remain rendered_pending_full_editorial_review. Contact sheets are not full audio/editorial review.
10. `status "JOB"` reads persisted progress. Update workspace STATUS.md with real checks/limits and deliver local files.

## Paths and cleanup

Jobs: library/manifests/clipping/<id>/job.json. Finals: output/final/<channel>/<job>/. Test-only intake --verification-only routes away from final content. Separate --revision identities protect existing work.

After **every finished clip**, including chosen extras, ask whether to delete source/transcript/work. `hermes-video-clipper retention --workspace PATH JOB` reports sizes and source dependencies; it deletes nothing. Explain remaining extras/revisions, get exact scope approval, protect finals/sidecars/music/models/code/catalogue, reject out-of-scope targets and links, save a receipt and verify protected hashes. No answer means keep.

No automatic uploads, compilation, extra narration or B-roll. Credit is not reuse permission. Successful rendering does not guarantee views, copyright clearance, monetization or payouts.
