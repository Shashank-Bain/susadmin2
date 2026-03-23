# susadmin2
Sustainability Admin

## Vercel Blob JSON Storage

This app can store JSON data in Vercel Blob instead of local files.

Set these environment variables:

- JSON_DB_BACKEND=vercel_blob
- BLOB_READ_WRITE_TOKEN=<your_vercel_blob_read_write_token>
- VERCEL_BLOB_ACCESS=public or private (default: public)
- VERCEL_BLOB_PREFIX=data/ (default: data/)

Optional:

- VERCEL_BLOB_BASE_URL=https://<store-id>.private.blob.vercel-storage.com
	- Works for private or public stores and avoids list lookups.
- VERCEL_BLOB_PUBLIC_BASE_URL=https://<store-id>.public.blob.vercel-storage.com
	- Backward-compatible alias for public stores.
- VERCEL_BLOB_PATH_OVERRIDES={"users.json":"custom/users.json"}
	- JSON mapping to override default per-file blob path.
- VERCEL_BLOB_TIMEOUT_SECONDS=10

Default blob path for a local file data/users.json is data/users.json.
