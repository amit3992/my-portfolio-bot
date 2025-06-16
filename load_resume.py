import os
import tempfile
import boto3
import pdfplumber
from dotenv import load_dotenv
from botocore.config import Config

load_dotenv()

def get_r2_client():
    return boto3.client(
        's3',
        endpoint_url='https://ee56f0babadac9d29676234c2f43ec81.r2.cloudflarestorage.com',
        aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
        config=Config(signature_version='s3v4'),
        region_name='auto'  # R2 uses 'auto' as region
    )


def extract_text_from_pdf(path: str) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join(
            page.extract_text() for page in pdf.pages if page.extract_text()
        )

def download_resume_from_r2(bucket_name: str, key: str) -> str:
    """Download resume from R2 and return its contents"""
    client = get_r2_client()
    
    # Create a temporary file to store the PDF
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        try:
            # Download the file from R2
            client.download_file(bucket_name, key, tmp_file.name)
            # Extract text from the downloaded PDF
            text = extract_text_from_pdf(tmp_file.name)
            return text
        finally:
            # Clean up the temporary file
            os.unlink(tmp_file.name)

def get_resume_from_r2() -> str:
    """Main function to get resume text"""
    bucket_name = os.getenv('R2_BUCKET_NAME')
    resume_key = os.getenv('R2_RESUME_KEY', 'resume.pdf')
    return download_resume_from_r2(bucket_name, resume_key)
