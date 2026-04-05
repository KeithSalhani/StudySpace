"""
Document processing module using Docling.
"""
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import AsrPipelineOptions, PdfPipelineOptions
from docling.document_converter import AudioFormatOption, DocumentConverter, PdfFormatOption
from pathlib import Path
import logging
from typing import List, Optional
from app.core.classification import Classifier

logger = logging.getLogger(__name__)

accelerator_options = AcceleratorOptions(
    device=AcceleratorDevice.CPU,
    num_threads=8,
)

DOC_PROCESSOR_SUPPORTED_SUFFIXES = tuple(
    sorted(
        {
            # Plain text is handled directly rather than through Docling.
            ".txt",
            ".text",
            # Common Docling document formats.
            ".pdf",
            ".docx",
            ".pptx",
            ".xlsx",
            ".md",
            ".markdown",
            ".html",
            ".htm",
            ".xhtml",
            ".adoc",
            ".asciidoc",
            ".asc",
            ".csv",
            ".vtt",
            ".tex",
            ".latex",
            # Common image formats covered by Docling's image input support.
            ".png",
            ".jpg",
            ".jpeg",
            ".bmp",
            ".gif",
            ".tif",
            ".tiff",
            ".webp",
            # Audio formats supported by Docling's ASR pipeline.
            ".mp3",
            ".wav",
            ".m4a",
            ".aac",
            ".flac",
            ".ogg",
            ".oga",
        }
    )
)

DOC_PROCESSOR_SUPPORTED_TYPES_LABEL = ", ".join(ext.lstrip(".") for ext in DOC_PROCESSOR_SUPPORTED_SUFFIXES)

class DocumentProcessor:
    def __init__(self):
        pdf_pipeline_options = PdfPipelineOptions()
        pdf_pipeline_options.accelerator_options = accelerator_options
        asr_pipeline_options = AsrPipelineOptions()
        # Force ASR to CPU because the local GTX 1050 Ti is below the CUDA
        # capability supported by the installed PyTorch build.
        asr_pipeline_options.accelerator_options.device = AcceleratorDevice.CPU
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pdf_pipeline_options,
                ),
                InputFormat.AUDIO: AudioFormatOption(
                    pipeline_options=asr_pipeline_options,
                ),
            }
        )
        self.classifier = Classifier()

    @staticmethod
    def get_supported_suffixes() -> tuple[str, ...]:
        return DOC_PROCESSOR_SUPPORTED_SUFFIXES

    @staticmethod
    def get_supported_types_label() -> str:
        return DOC_PROCESSOR_SUPPORTED_TYPES_LABEL

    @classmethod
    def supports_file(cls, filename: str) -> bool:
        suffix = Path(filename).suffix.lower()
        return suffix in cls.get_supported_suffixes()

    @classmethod
    def ensure_supported_file(cls, filename: str) -> None:
        if cls.supports_file(filename):
            return
        raise ValueError(
            "Unsupported file type. Supported types: "
            f"{cls.get_supported_types_label()}"
        )

    def process_document(self, file_path: str) -> str:
        """
        Process a supported document and convert it to markdown-like text.

        Args:
            file_path: Path to the document file

        Returns:
            str: Markdown or plain text content of the document
        """
        try:
            path = Path(file_path)

            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            self.ensure_supported_file(path.name)

            if path.suffix.lower() in {".txt", ".text"}:
                return self.process_text_file(file_path)

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
