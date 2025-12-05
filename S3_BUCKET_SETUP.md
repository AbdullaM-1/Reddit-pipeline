# S3 Bucket Setup for `reddit-sextstories`

## Quick Configuration

Add these to your `.env` file:

```env
# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1

# S3 Bucket Configuration
S3_BUCKET_NAME=reddit-sextstories
S3_PREFIX=posts/
```

## What Happens

After the pipeline runs and splits files, they will be automatically uploaded to:
```
s3://reddit-sextstories/posts/{post_id},{title},{correct_link}.json
```

## Troubleshooting "Cannot Copy S3 Objects"

If you're having trouble copying files from S3, here are solutions:

### 1. Verify Files Are Uploaded

```bash
# Check if files exist in S3
aws s3 ls s3://reddit-sextstories/posts/

# Count files
aws s3 ls s3://reddit-sextstories/posts/ | wc -l
```

### 2. Check AWS Permissions

Your AWS credentials need these permissions:
- `s3:PutObject` - to upload files
- `s3:GetObject` - to download/copy files
- `s3:ListBucket` - to list files

### 3. Copy Files from S3

```bash
# Copy single file
aws s3 cp s3://reddit-sextstories/posts/filename.json ./

# Copy all files
aws s3 sync s3://reddit-sextstories/posts/ ./local_directory/

# Copy with progress
aws s3 sync s3://reddit-sextstories/posts/ ./local_directory/ --exclude "*" --include "*.json"
```

### 4. IAM Policy Example

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::reddit-sextstories",
        "arn:aws:s3:::reddit-sextstories/*"
      ]
    }
  ]
}
```

## Pipeline Flow

1. Process posts → `pipeline_results.json`
2. Clean data → `pipeline_results.cleaned.json`
3. Flatten data → `pipeline_results.cleaned.flat.json`
4. Split files → `pipeline_results/posts_{timestamp}/`
5. **Upload to S3** → `s3://reddit-sextstories/posts/`

The upload happens automatically if `S3_BUCKET_NAME` is set in `.env`!

