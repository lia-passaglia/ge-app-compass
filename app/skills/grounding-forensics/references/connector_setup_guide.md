# corporate data connector setup guide

To ground Gemini Enterprise models with company-specific data and resolve dislike hotspots, follow these steps:

1. **google cloud storage (gcs) connector**:
   - Create a dedicated GCS bucket: `gs://<project-id>-grounding-data/`
   - Upload PDF/Markdown document archives.
   - Set IAM permission: Grant the Reasoning Engine's service account `roles/storage.objectViewer` on the bucket.
2. **google drive connector**:
   - Create a Shared Drive named "Gemini Grounding Docs".
   - Place all official contract templates, policy guidelines, and PDFs in the drive.
   - Connect using the Vertex AI Search Data Store integration with Drive-to-GCP syncing.
3. **verification**:
   - Instruct users to prepend prompts with grounding-triggering phrases or configure system-level data store attachments on the Reasoning Engine.
