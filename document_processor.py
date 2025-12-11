"""
Document processing module using Markitdown
"""
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from pathlib import Path
import logging
from typing import List, Optional
from classification import Classifier

logger = logging.getLogger(__name__)

accelerator_options = AcceleratorOptions(
    device=AcceleratorDevice.CPU,
    num_threads=8,
)

class DocumentProcessor:
    def __init__(self):
        pdf_pipeline_options = PdfPipelineOptions()
        pdf_pipeline_options.accelerator_options = accelerator_options
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pdf_pipeline_options,
                )
            }
        )
        self.classifier = Classifier()

    def process_document(self, file_path: str) -> str:
        """
        Process a document (PDF, DOCX, etc.) and convert to markdown

        Args:
            file_path: Path to the document file

        Returns:
            str: Markdown content of the document
        """
        try:
            path = Path(file_path)

            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            # Convert document to markdown
            result = self.converter.convert(file_path)

            if result is None:
                raise ValueError(f"Failed to process document: {file_path}")

            logger.info(f"Successfully processed document: {file_path}")
            return result.document.export_to_markdown()

        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            raise

    def classify_content(self, content: str, labels: List[str]) -> Optional[str]:
        """
        Classify the content and return the best matching label
        
        Args:
            content: Text content to classify
            labels: List of possible labels
            
        Returns:
            The predicted label with highest score
        """
        try:
            if not content or not labels:
                return None
                
            result = self.classifier.classify(content, labels)
            # Return label with highest score
            return result['labels'][0]
        except Exception as e:
            logger.error(f"Error classifying content: {str(e)}")
            return None

    def classify_content_full(self, content: str, labels: List[str]) -> Optional[dict]:
        """
        Classify the content and return the full result
        
        Args:
            content: Text content to classify
            labels: List of possible labels
            
        Returns:
            Dictionary containing labels and scores
        """
        try:
            if not content or not labels:
                return None
                
            return self.classifier.classify(content, labels)
        except Exception as e:
            logger.error(f"Error classifying content: {str(e)}")
            return None

    def process_text_file(self, file_path: str) -> str:
        """
        Process plain text files

        Args:
            file_path: Path to the text file

        Returns:
            str: Content of the text file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"Successfully processed text file: {file_path}")
            return content
        except Exception as e:
            logger.error(f"Error processing text file {file_path}: {str(e)}")
            raise
