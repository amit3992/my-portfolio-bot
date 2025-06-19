import os
import tempfile
import boto3
import logging
import pdfplumber
from dotenv import load_dotenv
from botocore.config import Config

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_r2_client():
    logger.debug("Initializing R2 client")
    try:
        client = boto3.client(
            's3',
            endpoint_url='https://ee56f0babadac9d29676234c2f43ec81.r2.cloudflarestorage.com',
            aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
            config=Config(signature_version='s3v4'),
            region_name='auto'  # R2 uses 'auto' as region
        )
        logger.debug("R2 client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize R2 client: {str(e)}")
        raise

def extract_text_from_pdf(path: str) -> str:
    logger.info(f"Extracting text from PDF: {path}")
    try:
        with pdfplumber.open(path) as pdf:
            text = "\n".join(
                page.extract_text() for page in pdf.pages if page.extract_text()
            )
            logger.debug(f"Successfully extracted {len(text)} characters from PDF")
            return text
    except Exception as e:
        logger.error(f"Failed to extract text from PDF {path}: {str(e)}")
        raise

def download_resume_from_r2(bucket_name: str, key: str) -> str:
    """Download resume from R2 and return its contents"""
    logger.info(f"Downloading resume from bucket: {bucket_name}, key: {key}")
    client = get_r2_client()
    
    # Create a temporary file to store the PDF
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        try:
            # Download the file from R2
            logger.debug(f"Downloading file to temporary location: {tmp_file.name}")
            client.download_file(bucket_name, key, tmp_file.name)
            
            # Extract text from the downloaded PDF
            text = extract_text_from_pdf(tmp_file.name)
            logger.info("Successfully downloaded and extracted resume text")
            return text
        except Exception as e:
            logger.error(f"Error processing resume: {str(e)}")
            raise
        finally:
            # Clean up the temporary file
            logger.debug(f"Cleaning up temporary file: {tmp_file.name}")
            os.unlink(tmp_file.name)

def get_resume_from_r2() -> str:
    """Main function to get resume text"""
    logger.info("Starting resume retrieval process")
    bucket_name = os.getenv('R2_BUCKET_NAME')
    resume_key = os.getenv('R2_RESUME_KEY', 'resume.pdf')
    
    if not bucket_name:
        logger.error("R2_BUCKET_NAME environment variable not set")
        raise ValueError("R2_BUCKET_NAME environment variable not set")
    
    try:
        return download_resume_from_r2(bucket_name, resume_key)
    except Exception as e:
        logger.error(f"Failed to get resume from R2: {str(e)}")
        raise
