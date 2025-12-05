# S3 Bucket Configuration

## Your S3 Bucket Setup

Based on your path `s3://reddit-sextstories/posts/`, configure your `.env` file:

```env
# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1

# S3 Bucket Configuration
S3_BUCKET_NAME=s3://reddit-sextstories/posts/
S3_PREFIX=posts/
```

## Upload Path Structure

Files will be uploaded to:
```
s3://reddit-sextstories/posts/{filename}.json
```

For example:
```
s3://reddit-sextstories/posts/1pdgyr2,Family_Traditions_Chapter_2,imgchest.com_p_abc123.json
```

## Troubleshooting "Cannot Copy S3 Objects"

If you're having trouble copying/downloading objects from S3, check:

### 1. AWS Credentials
Ensure your AWS credentials have read permissions:
- `s3:GetObject`
- `s3:ListBucket`

### 2. IAM Permissions Required

Your AWS user needs these permissions:

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

### 3. Verify Files Are Uploaded

Check if files were uploaded successfully:
- Look at pipeline output for upload confirmation
- Check AWS S3 Console: `s3://reddit-sextstories/posts/`
- Use AWS CLI: `aws s3 ls s3://reddit-sextstories/posts/`

## Testing S3 Connection

You can test your S3 connection with AWS CLI:

```bash
# List bucket contents
aws s3 ls s3://reddit-sextstories/posts/

# Copy a file from S3 (test download)
aws s3 cp s3://reddit-sextstories/posts/filename.json ./

# Copy all files from S3
aws s3 sync s3://reddit-sextstories/posts/ ./local_directory/
```

## Common Issues

### Issue: "Access Denied"
- **Solution**: Check IAM permissions
- Verify bucket policy allows your user

### Issue: "Bucket Not Found"
- **Solution**: Verify bucket name is correct (`reddit-sextstories`)
- Check region matches your bucket region

### Issue: "Cannot Copy Objects"
- **Solution**: Ensure you have `s3:GetObject` permission
- Check bucket policy allows downloads

