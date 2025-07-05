import boto3


def create_presigned_url_with_content_type(
    bucket_name, object_name, content_type, expiration=604800
):
    s3_client = boto3.client("s3")

    # Notice the addition of 'ContentType'
    params = {"Bucket": bucket_name, "Key": object_name, "ContentType": content_type}

    response = s3_client.generate_presigned_url(
        "put_object", Params=params, ExpiresIn=expiration
    )
    return response


url = create_presigned_url_with_content_type(
    "fiap-video-processor-bucket",
    "videos/e2ed3910-3d49-4aa2-95cb-d8e4d6c53145/NyanCat.mp4",
    "video/mp4",  # MUST MATCH THE HEADER IN THE PUT REQUEST
)
print(url)
