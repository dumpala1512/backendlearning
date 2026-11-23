# Local AWS Environment Orientation Proof

**Date:** 06 November 2026

**Environment**

- Local AWS simulator: Floci
- Endpoint: `http://localhost:4566`
- AWS CLI configured with local endpoint
- No requests were sent to a real AWS account.

---

# 1. Amazon S3

## Create Bucket

**Command**

```bash
aws --endpoint-url=http://localhost:4566 s3 mb s3://my-demo-bucket
```

**Output**

```text
make_bucket: my-demo-bucket
```

## Verify Bucket Exists

**Command**

```bash
aws --endpoint-url=http://localhost:4566 s3 ls
```

**Output**

```text
2026-11-06 17:02:37 my-demo-bucket
```

Alternative verification

```bash
aws s3api list-buckets --endpoint-url http://localhost:4566 --output table
```

Output

```
Bucket Name : my-demo-bucket
CreationDate: 2026-11-06T11:32:37+00:00
```

**Result**

✔ Bucket successfully created and verified.

---

# 2. AWS Secrets Manager

## Create Secret

**Command**

```bash
aws --endpoint-url=http://localhost:4566 secretsmanager create-secret \
    --name MySecret \
    --secret-string "HelloWorld"
```

**Output**

```json
{
  "Name": "MySecret",
  "ARN": "arn:aws:secretsmanager:us-east-1:000000000000:secret:MySecret-..."
}
```

## Retrieve Secret

**Command**

```bash
aws --endpoint-url=http://localhost:4566 secretsmanager get-secret-value \
    --secret-id MySecret
```

**Output**

```json
{
  "Name": "MySecret",
  "SecretString": "HelloWorld"
}
```

**Verification**

Stored value:

```
HelloWorld
```

Retrieved value:

```
HelloWorld
```

✔ Values match exactly.

---

# 3. Amazon SQS

## Create Queue

**Command**

```bash
aws --endpoint-url=http://localhost:4566 sqs create-queue \
    --queue-name demo-queue
```

**Output**

```json
{
  "QueueUrl":"http://localhost:4566/000000000000/demo-queue"
}
```

---

## Send Message

**Command**

```bash
aws --endpoint-url=http://localhost:4566 sqs send-message \
    --queue-url http://localhost:4566/000000000000/demo-queue \
    --message-body "Hello AWS"
```

**Output**

```json
{
  "MessageId":"eaa88e0c-cef1-4b0c-94c7-60d1399e947f"
}
```

---

## Receive Message

**Command**

```bash
aws --endpoint-url=http://localhost:4566 sqs receive-message \
    --queue-url http://localhost:4566/000000000000/demo-queue
```

**Output**

```json
{
  "Messages":[
    {
      "Body":"Hello AWS"
    }
  ]
}
```

✔ Message successfully received.

---

## Delete (Acknowledge) Message

**Command**

```bash
aws --endpoint-url=http://localhost:4566 sqs delete-message \
    --queue-url http://localhost:4566/000000000000/demo-queue \
    --receipt-handle "<ReceiptHandle>"
```

**Expected Output**

```
(no output)
```

---

## Verify Queue Is Empty

**Command**

```bash
aws --endpoint-url=http://localhost:4566 sqs receive-message \
    --queue-url http://localhost:4566/000000000000/demo-queue
```

**Expected Output**

```json
{}
```

Alternatively

```bash
aws --endpoint-url=http://localhost:4566 sqs get-queue-attributes \
    --queue-url http://localhost:4566/000000000000/demo-queue \
    --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible
```

Expected

```json
{
  "Attributes": {
    "ApproximateNumberOfMessages": "0",
    "ApproximateNumberOfMessagesNotVisible": "0"
  }
}
```

✔ Queue successfully emptied after acknowledgement.

---

# Conclusion

This exercise confirms that:

- Floci is running locally.
- AWS CLI communicates only with Floci through `http://localhost:4566`.
- Amazon S3 bucket creation and listing work correctly.
- AWS Secrets Manager stores and retrieves secrets correctly.
- Amazon SQS queue creation, message sending, receiving, acknowledgement (deletion), and verification all work correctly.

The local AWS simulation is fully operational and ready for SDK-based development.