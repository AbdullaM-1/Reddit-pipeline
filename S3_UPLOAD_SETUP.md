# S3 Bucket Upload Setup

## Overview

The pipeline now automatically uploads split files to an S3 bucket after splitting. This feature is optional and requires boto3 and AWS credentials.

## Setup Steps

### 1. Install boto3

```bash
pip install boto3
```

Or install from requirements.txt:
```bash
pip install -r requirements.txt
```

### 2. Configure AWS Credentials

Add the following to your `.env` file:

```env
# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1

# S3 Bucket Configuration
S3_BUCKET_NAME=your-bucket-name
S3_PREFIX=posts/2024
```

### 3. AWS IAM Permissions

Your AWS user/role needs the following S3 permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::your-bucket-name/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::your-bucket-name"
    }
  ]
}
```

## How It Works

### Automatic Upload Flow

1. Pipeline processes posts
2. Cleans and flattens data
3. **Splits into individual files**
4. **Automatically uploads to S3** ← New!

### Upload Process

- Uploads all JSON files from the split directory
- Uses the filename as the S3 key
- Optional S3 prefix for organization
- Progress tracking every 50 files
- Error handling for failed uploads

### S3 Structure

Files are uploaded with this structure:

```
s3://your-bucket-name/
└── posts/2024/  (if S3_PREFIX is set)
    ├── 1pdgyr2,Family_Traditions_Chapter_2,imgchest.com_p_abc123.json
    ├── 2abc123,Another_Story_Part_1,imgchest.com_p_def456.json
    └── ...
```

Or if no prefix:
```
s3://your-bucket-name/
├── 1pdgyr2,Family_Traditions_Chapter_2,imgchest.com_p_abc123.json
├── 2abc123,Another_Story_Part_1,imgchest.com_p_def456.json
└── ...
```

## Configuration Options

### Required Environment Variables

- `AWS_ACCESS_KEY_ID` - Your AWS access key
- `AWS_SECRET_ACCESS_KEY` - Your AWS secret key
- `S3_BUCKET_NAME` - Name of your S3 bucket

### Optional Environment Variables

- `AWS_REGION` - AWS region (default: `us-east-1`)
- `S3_PREFIX` - S3 key prefix for organizing files (e.g., `posts/2024/`)

## Example Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Uploading split files to S3 bucket...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Uploading 150 files to S3 bucket: my-reddit-posts-bucket
S3 prefix: posts/2024/

[50/150] Uploaded 50 files...
[100/150] Uploaded 100 files...
[150/150] Uploaded 150 files...

✓ S3 Upload Complete!
  Uploaded: 150/150 files
S3 Location: s3://my-reddit-posts-bucket/posts/2024/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓✓✓ PIPELINE COMPLETE ✓✓✓
✓ Files uploaded to S3 bucket: my-reddit-posts-bucket
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Features

✅ **Automatic Upload** - Runs after splitting files  
✅ **Progress Tracking** - Shows progress every 50 files  
✅ **Error Handling** - Continues on individual file failures  
✅ **Flexible Prefix** - Organize files with S3 prefix  
✅ **Optional Feature** - Works even if S3 not configured  

## Troubleshooting

### S3 Upload Skipped

If you see "S3 upload skipped", check:

1. **boto3 installed?**
   ```bash
   pip install boto3
   ```

2. **AWS credentials in .env?**
   - Check `AWS_ACCESS_KEY_ID`
   - Check `AWS_SECRET_ACCESS_KEY`

3. **S3 bucket name set?**
   - Check `S3_BUCKET_NAME` in .env

### Upload Failures

Common issues:

- **Invalid credentials**: Check your AWS access keys
- **Bucket doesn't exist**: Create the bucket in AWS Console
- **Insufficient permissions**: Check IAM permissions
- **Region mismatch**: Ensure `AWS_REGION` matches bucket region

### Skip S3 Upload

To skip S3 upload, simply don't set `S3_BUCKET_NAME` in your `.env` file. The pipeline will still run and create local files.

