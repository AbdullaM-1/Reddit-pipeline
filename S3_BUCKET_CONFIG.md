# S3 Bucket Configuration for `reddit-sextstories`

## Your S3 Bucket Setup

Based on your path `s3://reddit-sextstories/posts/`, configure your `.env` file:

```env
# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1

# S3 Bucket Configuration
S3_BUCKET_NAME=reddit-sextstories
S3_PREFIX=posts/
```

## File Upload Location

After the pipeline runs, files will be uploaded to:
```
s3://reddit-sextstories/posts/{filename}.json
```

Example:
```
s3://reddit-sextstories/posts/1pdgyr2,Family_Traditions_Chapter_2,imgchest.com_p_abc123.json
```

## Troubleshooting "Cannot Copy S3 Objects"

If you're having trouble copying/downloading objects from S3:

### 1. Check AWS Permissions

Your AWS credentials need these permissions:

**Required IAM Policy:**
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
        "arn:aws:s3:::reddit-sextstories/*",
        "arn:aws:s3:::reddit-sextstories"
      ]
    }
  ]
}
```

### 2. Verify Files Are Uploaded

Check if files exist in S3:
```bash
# List files in bucket
aws s3 ls s3://reddit-sextstories/posts/

# Count files
aws s3 ls s3://reddit-sextstories/posts/ | wc -l
```

### 3. Test Copying from S3

```bash
# Copy a single file
aws s3 cp s3://reddit-sextstories/posts/filename.json ./

# Copy all files
aws s3 sync s3://reddit-sextstories/posts/ ./local_directory/

# Copy with preserve path structure
aws s3 sync s3://reddit-sextstories/posts/ ./local_directory/ --exclude "*" --include "*.json"
```

### 4. Common Issues

**Issue: "Access Denied"**
- Check IAM permissions include `s3:GetObject` and `s3:ListBucket`
- Verify bucket policy allows your user/role

**Issue: "Bucket Not Found"**
- Verify bucket name is exactly `reddit-sextstories`
- Check you're using the correct AWS region

**Issue: "Cannot Copy Objects"**
- Ensure your AWS credentials have read permissions
- Check bucket policy allows downloads
- Verify you're authenticated with correct AWS account

## Pipeline Configuration

The pipeline is already configured to upload to your bucket. Just set these in `.env`:

```env
S3_BUCKET_NAME=reddit-sextstories
S3_PREFIX=posts/
```

Files will automatically upload after splitting!

