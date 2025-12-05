# S3 Bucket Setup - `reddit-sextstories`

## Quick Setup

### 1. Configure `.env` file

Add these variables to your `.env` file:

```env
# AWS Credentials
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1

# S3 Bucket Configuration
S3_BUCKET_NAME=reddit-sextstories
S3_PREFIX=posts/
```

### 2. Install boto3

```bash
pip install boto3
```

Or:
```bash
pip install -r requirements.txt
```

## Upload Path

Files will be uploaded to:
```
s3://reddit-sextstories/posts/{filename}.json
```

Example:
```
s3://reddit-sextstories/posts/1pdgyr2,Family_Traditions_Chapter_2,imgchest.com_p_abc123.json
```

## Troubleshooting "Cannot Copy S3 Objects"

If you're having trouble copying files from S3:

### Check 1: Verify Files Exist

```bash
aws s3 ls s3://reddit-sextstories/posts/
```

### Check 2: Verify Permissions

Your AWS user needs:
- `s3:PutObject` - Upload files
- `s3:GetObject` - Download/copy files  
- `s3:ListBucket` - List files

### Check 3: Copy Files from S3

```bash
# Copy all files
aws s3 sync s3://reddit-sextstories/posts/ ./local_directory/

# Copy single file
aws s3 cp s3://reddit-sextstories/posts/filename.json ./
```

## Pipeline Integration

The S3 upload is **already integrated** into the pipeline! 

Just set:
- `S3_BUCKET_NAME=reddit-sextstories`
- `S3_PREFIX=posts/`

And files will automatically upload after splitting!

