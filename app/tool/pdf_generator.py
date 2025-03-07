import os
import uuid
import json
import datetime
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

# Try to import reportlab, but make it optional
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, Preformatted
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Try to import markdown, but make it optional
try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

from pydantic import BaseModel, Field
import io
import subprocess

# Try to import matplotlib, but make it optional
try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from app.tool.base import BaseTool
from app.schema import DocumentFormat, GenerateDocumentInput, VisualizationData, DataTable, DocumentGenerationOptions
from app.exceptions import DocumentGenerationError
from app.config import config
from app.tool.markdown_generator import MarkdownGeneratorTool  # Fallback to markdown if PDF not available


# Define a Pydantic model for the tool parameters
class PDFGeneratorParams(BaseModel):
    content: str = Field(..., description="Content for the PDF document")
    output_path: Optional[str] = Field(None, description="Path to save the PDF file (optional)")
    title: Optional[str] = Field(None, description="Document title (optional)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata for the document (optional)")
    visualizations: Optional[List[Dict[str, Any]]] = Field(None, description="Visualizations to include in the document (optional)")
    data_tables: Optional[List[Dict[str, Any]]] = Field(None, description="Data tables to include in the document (optional)")
    options: Optional[Dict[str, Any]] = Field(None, description="Additional options for document generation (optional)")


class PDFGeneratorTool(BaseTool):
    """Tool for generating PDF documents with support for data tables and visualizations."""
    
    def __init__(self):
        """Initialize the PDF generator tool."""
        parameters = {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Content for the PDF document"
                },
                "output_path": {
                    "type": "string",
                    "description": "Path to save the PDF file (optional)"
                },
                "title": {
                    "type": "string",
                    "description": "Document title (optional)"
                },
                "metadata": {
                    "type": "object",
                    "description": "Additional metadata for the document (optional)"
                },
                "visualizations": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    },
                    "description": "Visualizations to include in the document (optional)"
                },
                "data_tables": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    },
                    "description": "Data tables to include in the document (optional)"
                },
                "options": {
                    "type": "object",
                    "description": "Additional options for document generation (optional)"
                }
            },
            "required": ["content"]
        }
        
        super().__init__(
            name="pdf_generator",
            description="Generate PDF documents from text content with support for data tables and visualizations",
            parameters=parameters
        )
        
        # Create artifacts directory if it doesn't exist
        self.artifacts_dir = config.get_nested_value(["artifacts", "base_dir"], "./artifacts")
        self.pdf_artifacts_dir = os.path.join(self.artifacts_dir, "pdf")
        self.visualization_artifacts_dir = os.path.join(self.artifacts_dir, "visualizations")
        os.makedirs(self.pdf_artifacts_dir, exist_ok=True)
        os.makedirs(self.visualization_artifacts_dir, exist_ok=True)
        
        # Initialize custom styles
        self._initialize_styles()
    
    def _initialize_styles(self):
        """Initialize custom styles for PDF documents."""
        if not REPORTLAB_AVAILABLE:
            return
            
        self.styles = getSampleStyleSheet()
        
        # Add custom heading styles with unique names
        self.styles.add(ParagraphStyle(
            name='CustomHeading1',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=12,
            spaceBefore=12,
            textColor=colors.darkblue
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=10,
            spaceBefore=10,
            textColor=colors.darkblue
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading3',
            parent=self.styles['Heading3'],
            fontSize=14,
            spaceAfter=8,
            spaceBefore=8,
            textColor=colors.darkblue
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading4',
            parent=self.styles['Heading4'],
            fontSize=12,
            spaceAfter=6,
            spaceBefore=6,
            textColor=colors.darkblue
        ))
        
        # Add custom body text style
        self.styles.add(ParagraphStyle(
            name='CustomBodyText',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=14,
            spaceBefore=6,
            spaceAfter=6
        ))
        
        # Add custom code style
        self.styles.add(ParagraphStyle(
            name='CodeBlock',
            parent=self.styles['Code'],
            fontSize=10,
            fontName='Courier',
            leading=12,
            spaceBefore=6,
            spaceAfter=6,
            backColor=colors.lightgrey,
            borderWidth=1,
            borderColor=colors.grey,
            borderRadius=2,
            borderPadding=5
        ))
        
        # Add custom code header style
        self.styles.add(ParagraphStyle(
            name='CustomCodeHeader',
            parent=self.styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor=colors.darkblue,
            spaceBefore=6,
            spaceAfter=2
        ))
        
        # Add custom code style for Preformatted text
        self.styles.add(ParagraphStyle(
            name='CustomCode',
            parent=self.styles['Code'],
            fontSize=9,
            fontName='Courier',
            leading=11,
            textColor=colors.black,
            backColor=colors.lightgrey
        ))
        
        # Add custom bullet item style
        self.styles.add(ParagraphStyle(
            name='CustomBulletItem',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=14,
            leftIndent=20,
            spaceBefore=2,
            spaceAfter=2
        ))
        
        # Add custom numbered item style
        self.styles.add(ParagraphStyle(
            name='CustomNumberItem',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=14,
            leftIndent=20,
            spaceBefore=2,
            spaceAfter=2
        ))
        
        # Add visualization suggestion style
        self.styles.add(ParagraphStyle(
            name='CustomVisualizationSuggestion',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14,
            leftIndent=20,
            rightIndent=20,
            spaceBefore=5,
            spaceAfter=5,
            backColor=colors.lavender,
            borderWidth=1,
            borderColor=colors.darkblue,
            borderPadding=8,
            borderRadius=5
        ))
        
        # Add visualization placeholder style
        self.styles.add(ParagraphStyle(
            name='CustomVisPlaceholder',
            parent=self.styles['Normal'],
            fontSize=12,
            leading=16,
            alignment=1,  # Center
            spaceBefore=10,
            spaceAfter=10,
            backColor=colors.lightgrey,
            borderWidth=1,
            borderColor=colors.grey,
            borderPadding=20,
            borderRadius=5
        ))
    
    def _save_artifact(self, pdf_path: str, title: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Save PDF as an artifact.
        
        Args:
            pdf_path (str): Path to the PDF file
            title (Optional[str]): Title of the PDF
            metadata (Optional[Dict[str, Any]]): Additional metadata
            
        Returns:
            str: Path to the saved artifact
        """
        # Generate a unique ID for this artifact
        artifact_id = str(uuid.uuid4())
        
        # Create filename if title is provided
        if title:
            safe_title = "".join(c if c.isalnum() else "_" for c in title[:30]).lower()
            filename = f"{safe_title}_{artifact_id[:8]}.pdf"
        else:
            filename = f"document_{artifact_id[:8]}.pdf"
        
        # Create artifact path
        artifact_path = os.path.join(self.pdf_artifacts_dir, filename)
        
        # Copy the PDF to the artifacts directory
        import shutil
        shutil.copy2(pdf_path, artifact_path)
        
        # Create metadata
        artifact_metadata = {
            "id": artifact_id,
            "type": "pdf",
            "title": title if title else "Untitled Document",
            "filename": filename,
            "created_at": datetime.datetime.now().isoformat(),
        }
        
        # Add additional metadata if provided
        if metadata:
            artifact_metadata.update(metadata)
        
        # Save metadata file
        metadata_path = f"{artifact_path}.meta.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(artifact_metadata, f, indent=2)
        
        self.logger.info(f"PDF artifact saved to {artifact_path}")
        return artifact_path
    
    def _create_visualization(self, viz_data: Dict[str, Any]) -> Optional[List[Any]]:
        """
        Create a visualization for the PDF document.
        
        Args:
            viz_data (Dict[str, Any]): Visualization data
            
        Returns:
            Optional[List[Any]]: List of PDF elements for the visualization
        """
        if not REPORTLAB_AVAILABLE:
            return None
            
        try:
            elements = []
            
            # Extract visualization information
            title = viz_data.get("title", "Visualization")
            description = viz_data.get("description", "")
            viz_type = viz_data.get("type", "").lower()
            
            # Add title
            elements.append(Paragraph(title, self.styles['CustomHeading3']))
            
            # Add description if provided
            if description:
                elements.append(Paragraph(description, self.styles['CustomBodyText']))
                elements.append(Spacer(1, 0.1*inch))
            
            # If this is just a suggestion, format it nicely
            if "data" not in viz_data or not viz_data.get("data"):
                # This is a visualization suggestion, not actual data
                suggestion_text = f"Suggested visualization: {viz_type.upper()}"
                
                # Add axes information if available
                if "x_axis" in viz_data and viz_data["x_axis"]:
                    suggestion_text += f"\nX-axis: {viz_data['x_axis']}"
                    
                if "y_axis" in viz_data and viz_data["y_axis"]:
                    suggestion_text += f"\nY-axis: {viz_data['y_axis']}"
                
                elements.append(Paragraph(suggestion_text, self.styles['CustomVisualizationSuggestion']))
                elements.append(Spacer(1, 0.1*inch))
                return elements
                
            # Get the visualization data
            data = viz_data.get("data", {})
            if not data:
                self.logger.warning(f"No data provided for visualization: {title}")
                return elements
                
            # Create a default placeholder image for now
            # In a real implementation, we would generate the visualization based on the data
            # using matplotlib, plotly, or another visualization library
            
            # For now, just add a placeholder box with the visualization type
            elements.append(Paragraph(f"[{viz_type.upper()} VISUALIZATION]", self.styles['CustomVisPlaceholder']))
            elements.append(Spacer(1, 0.1*inch))
            
            # Note: In a future implementation, we would create the actual visualization here
            # For example, using matplotlib:
            # fig = Figure(figsize=(6, 4))
            # ax = fig.add_subplot(111)
            # ... create the visualization based on viz_type and data ...
            # img_path = os.path.join(self.visualization_artifacts_dir, f"{uuid.uuid4()}.png")
            # fig.savefig(img_path)
            # img = Image(img_path, width=6*inch, height=4*inch)
            # elements.append(img)
            
            return elements
            
        except Exception as e:
            self.logger.error(f"Error creating visualization: {str(e)}")
            return None
    
    def _create_data_table(self, table_data: Dict[str, Any]) -> Optional[List[Any]]:
        """
        Create a data table for the PDF document.
        
        Args:
            table_data (Dict[str, Any]): Table data including title, columns, and rows
            
        Returns:
            Optional[List[Any]]: List of PDF elements for the table
        """
        if not REPORTLAB_AVAILABLE:
            return None
            
        try:
            elements = []
            
            # Extract table data
            title = table_data.get("title", "Data Table")
            description = table_data.get("description", "")
            columns = table_data.get("columns", [])
            rows = table_data.get("rows", [])
            
            # Validate data
            if not columns or not rows:
                self.logger.warning(f"Table {title} has no columns or rows")
                return None
                
            # Add title
            elements.append(Paragraph(title, self.styles['CustomHeading3']))
            
            # Add description if provided
            if description:
                elements.append(Paragraph(description, self.styles['CustomBodyText']))
                elements.append(Spacer(1, 0.1*inch))
            
            # Create table data including header row
            table_data = [columns]
            for row in rows:
                # Make sure row has the same length as columns
                if len(row) < len(columns):
                    row.extend([""] * (len(columns) - len(row)))
                elif len(row) > len(columns):
                    row = row[:len(columns)]
                table_data.append(row)
            
            # Create table
            table = Table(table_data, colWidths=[1.5*inch] * len(columns))
            
            # Add table style
            style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ])
            
            # Add alternating row colors
            for i in range(1, len(table_data)):
                if i % 2 == 0:
                    style.add('BACKGROUND', (0, i), (-1, i), colors.lightgrey)
            
            table.setStyle(style)
            elements.append(table)
            
            return elements
            
        except Exception as e:
            self.logger.error(f"Error creating data table: {str(e)}")
            return None
    
    def _markdown_to_elements(self, markdown_content: str) -> List[Any]:
        """
        Convert markdown content to ReportLab elements.
        
        Args:
            markdown_content (str): Content in markdown format
            
        Returns:
            List[Any]: List of ReportLab elements
        """
        elements = []
        
        # Split content into blocks
        blocks = re.split(r'\n\n+', markdown_content)
        
        # Process each block
        for block in blocks:
            if not block.strip():
                continue
                
            # Check for headers
            header_match = re.match(r'^(#{1,6})\s+(.+)$', block)
            if header_match:
                level = len(header_match.group(1))
                text = header_match.group(2).strip()
                
                if level == 1:
                    elements.append(Spacer(1, 0.3*inch))
                    elements.append(Paragraph(text, self.styles['CustomHeading1']))
                    elements.append(Spacer(1, 0.2*inch))
                elif level == 2:
                    elements.append(Spacer(1, 0.25*inch))
                    elements.append(Paragraph(text, self.styles['CustomHeading2']))
                    elements.append(Spacer(1, 0.15*inch))
                elif level == 3:
                    elements.append(Spacer(1, 0.2*inch))
                    elements.append(Paragraph(text, self.styles['CustomHeading3']))
                    elements.append(Spacer(1, 0.1*inch))
                else:
                    elements.append(Spacer(1, 0.15*inch))
                    elements.append(Paragraph(text, self.styles['CustomHeading4']))
                    elements.append(Spacer(1, 0.1*inch))
                continue
                
            # Check for code blocks
            code_match = re.match(r'^```(.+?)?$\n(.+?)\n```$', block, re.DOTALL)
            if code_match:
                language = code_match.group(1).strip() if code_match.group(1) else ""
                code = code_match.group(2)
                
                # Add language as a mini-header if provided
                if language:
                    elements.append(Paragraph(f"Code ({language}):", self.styles['CustomCodeHeader']))
                
                elements.append(Spacer(1, 0.1*inch))
                elements.append(Preformatted(code, self.styles['CustomCode']))
                elements.append(Spacer(1, 0.1*inch))
                continue
                
            # Check for unordered lists
            if re.match(r'^(\s*[-*+]\s+)', block):
                list_items = re.split(r'\n(?=\s*[-*+]\s+)', block)
                
                # Create a flowable list container
                bullet_list = []
                
                for item in list_items:
                    # Extract the list item text and check for the marker used
                    marker_match = re.match(r'^\s*([-*+])\s+(.+)$', item, re.DOTALL)
                    if marker_match:
                        marker = marker_match.group(1)
                        item_text = marker_match.group(2).strip()
                        
                        # Process nested formatting within list items
                        item_text = re.sub(r'\*\*(.*?)\*\*|__(.*?)__', r'<b>\1\2</b>', item_text)
                        item_text = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)|_(.*?)_', r'<i>\1\2</i>', item_text)
                        item_text = re.sub(r'`(.*?)`', r'<code>\1</code>', item_text)
                        
                        # Create a bullet item with proper indentation
                        bullet_item = Paragraph(f"• {item_text}", self.styles['CustomBulletItem'])
                        elements.append(bullet_item)
                        elements.append(Spacer(1, 0.05*inch))
                
                elements.append(Spacer(1, 0.1*inch))
                continue
                
            # Check for ordered lists
            if re.match(r'^(\s*\d+\.\s+)', block):
                list_items = re.split(r'\n(?=\s*\d+\.\s+)', block)
                
                for i, item in enumerate(list_items):
                    # Extract the list item text
                    item_text = re.sub(r'^\s*\d+\.\s+', '', item).strip()
                    
                    # Process nested formatting within list items
                    item_text = re.sub(r'\*\*(.*?)\*\*|__(.*?)__', r'<b>\1\2</b>', item_text)
                    item_text = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)|_(.*?)_', r'<i>\1\2</i>', item_text)
                    item_text = re.sub(r'`(.*?)`', r'<code>\1</code>', item_text)
                    
                    # Create a numbered item with proper indentation
                    number_item = Paragraph(f"{i+1}. {item_text}", self.styles['CustomNumberItem'])
                    elements.append(number_item)
                    elements.append(Spacer(1, 0.05*inch))
                
                elements.append(Spacer(1, 0.1*inch))
                continue
            
            # Process paragraphs - add better markdown processing for bold, italic, etc.
            text = block.strip()
            
            # Process inline formatting
            # Italic: *text* or _text_
            text = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)|_(.*?)_', r'<i>\1\2</i>', text)
            
            # Bold: **text** or __text__
            text = re.sub(r'\*\*(.*?)\*\*|__(.*?)__', r'<b>\1\2</b>', text)
            
            # Code: `text`
            text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
            
            # Create paragraph with processed text
            elements.append(Paragraph(text, self.styles['CustomBodyText']))
            elements.append(Spacer(1, 0.15*inch))
        
        return elements

    def _run(self, 
             content: str, 
             output_path: Optional[str] = None, 
             title: Optional[str] = None, 
             metadata: Optional[Dict[str, Any]] = None,
             visualizations: Optional[List[Dict[str, Any]]] = None,
             data_tables: Optional[List[Dict[str, Any]]] = None,
             options: Optional[Dict[str, Any]] = None,
             action: Optional[str] = None,
             file_name: Optional[str] = None,
             file_path: Optional[str] = None,
             file: Optional[str] = None,
             text: Optional[str] = None,
             format: Optional[str] = None,
             document_path: Optional[str] = None,
             **kwargs) -> Dict[str, Any]:
        """
        Generate a PDF document.
        
        Args:
            content (str): Content for the PDF document
            output_path (str, optional): Path to save the PDF file
            title (str, optional): Document title
            metadata (Dict[str, Any], optional): Document metadata
            visualizations (List[Dict[str, Any]], optional): Visualizations to include
            data_tables (List[Dict[str, Any]], optional): Data tables to include
            options (Dict[str, Any], optional): Additional options for document generation
            action (str, optional): Action parameter (ignored, for compatibility)
            file_name (str, optional): Alternative name for the output file (ignored, use output_path instead)
            file_path (str, optional): Alternative path for the output file (ignored, use output_path instead)
            file (str, optional): Alternative parameter for output file (ignored, use output_path instead)
            text (str, optional): Alternative parameter for content (will be used if content is empty)
            format (str, optional): Output format (ignored for PDF generator)
            document_path (str, optional): Path to a document to use as source (if content is empty)
            **kwargs: Any other parameters (ignored for compatibility)
            
        Returns:
            Dict[str, Any]: Dictionary containing path to the generated PDF file and additional information
        """
        # Use text parameter as content if content is empty
        if not content and text:
            content = text
            
        # Handle document_path if provided and content is empty
        if not content and document_path:
            try:
                with open(document_path, 'r', encoding='utf-8') as doc_file:
                    content = doc_file.read()
                self.logger.info(f"Using content from document_path: {document_path}")
            except Exception as e:
                self.logger.error(f"Could not read document_path '{document_path}': {str(e)}")
                content = f"Failed to load content from {document_path}"
            
        # Handle file parameter as an alternative to output_path if output_path is not provided
        if not output_path and file:
            output_path = file
            
        # Then handle file_path parameter as an alternative to output_path if output_path is still not provided
        if not output_path and file_path:
            output_path = file_path
        
        # Handle file_name parameter to append to output directory if output_path is still not provided
        if not output_path and file_name:
            # Use default output directory
            output_dir = config.get_nested_value(["document", "pdf_output_dir"], "./output/pdf")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, file_name)
        
        # Set default output_path if not provided
        if not output_path:
            # Use default output directory from config
            output_dir = config.get_nested_value(["document", "pdf_output_dir"], "./output/pdf")
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filename from title or use default with timestamp for uniqueness
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{title.lower().replace(' ', '_')}_{timestamp}.pdf" if title else f"document_{timestamp}.pdf"
            output_path = os.path.join(output_dir, filename)
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                self.logger.error(f"Could not create output directory '{output_dir}': {str(e)}")
                # Fall back to a directory we know exists
                fallback_dir = "./output/pdf"
                os.makedirs(fallback_dir, exist_ok=True)
                output_path = os.path.join(fallback_dir, os.path.basename(output_path))
                
        # Remove placeholder paths - if output_path contains placeholder text like 'path/to/'
        if "path/to" in output_path:
            # Use default output directory from config
            output_dir = config.get_nested_value(["document", "pdf_output_dir"], "./output/pdf")
            os.makedirs(output_dir, exist_ok=True)
            
            # Use just the filename part or create a default with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(output_path)
            if filename == "output.pdf":  # This was a placeholder
                filename = f"{title.lower().replace(' ', '_')}_{timestamp}.pdf" if title else f"document_{timestamp}.pdf"
            
            output_path = os.path.join(output_dir, filename)
        
        # Check if reportlab is available
        if not REPORTLAB_AVAILABLE:
            self.logger.warning("ReportLab is not installed. Falling back to Markdown generation.")
            # Fall back to markdown generator
            markdown_tool = MarkdownGeneratorTool()
            markdown_result = markdown_tool.run(
                content=content,
                output_path=output_path.replace('.pdf', '.md') if output_path else None,
                title=title,
                metadata=metadata,
                options=options
            )
            
            # Return result with fallback information
            result = markdown_result.copy()
            result["fallback"] = "pdf_not_available"
            result["message"] = "PDF generation requires ReportLab. Install with: pip install reportlab"
            return result
        
        try:
            # Create PDF document
            doc = SimpleDocTemplate(output_path, pagesize=letter)
            
            # Create document elements
            elements = []
            
            # Add title if provided
            if title:
                elements.append(Paragraph(title, self.styles['Title']))
                elements.append(Spacer(1, 0.25*inch))
            
            # Process content - detect if it's markdown and process accordingly
            is_markdown = False
            if '```' in content or content.startswith('#') or re.search(r'^\s*[-*]\s+', content, re.MULTILINE):
                is_markdown = True
                
            if is_markdown:
                # Process as markdown
                markdown_elements = self._markdown_to_elements(content)
                elements.extend(markdown_elements)
            else:
                # Process as plain text
                paragraphs = content.split('\n\n')
                for paragraph in paragraphs:
                    if paragraph.strip():
                        elements.append(Paragraph(paragraph.strip(), self.styles['CustomBodyText']))
                        elements.append(Spacer(1, 0.1*inch))
            
            # Add visualizations if provided
            if visualizations:
                for viz_data in visualizations:
                    viz_elements = self._create_visualization(viz_data)
                    if viz_elements:
                        elements.append(Spacer(1, 0.2*inch))
                        elements.extend(viz_elements)
                        elements.append(Spacer(1, 0.2*inch))
            
            # Add data tables if provided
            if data_tables:
                for table_data in data_tables:
                    table_elements = self._create_data_table(table_data)
                    if table_elements:
                        elements.append(Spacer(1, 0.2*inch))
                        elements.extend(table_elements)
                        elements.append(Spacer(1, 0.2*inch))
            
            # Build document
            doc.build(elements)
            
            # Save as artifact
            artifact_path = self._save_artifact(output_path, title, metadata)
            
            # Return result without including large content strings
            result = {
                "path": output_path,
                "artifact_path": artifact_path,
                "file_type": "pdf",
                "status": "success",
                "message": f"Generated PDF document: {os.path.basename(output_path)}"
            }
            
            # Add metadata if provided, but exclude large content objects
            if metadata:
                # Filter out any large content fields to avoid terminal clutter
                filtered_metadata = {k: v for k, v in metadata.items() 
                                  if not isinstance(v, str) or len(v) < 500}
                result["metadata"] = filtered_metadata
                
            # Include minimal visualization info without the full data
            if visualizations:
                viz_info = []
                for viz in visualizations:
                    viz_info.append({
                        "title": viz.get("title", "Untitled"),
                        "type": viz.get("type", ""),
                        "included": True
                    })
                result["visualizations"] = viz_info
                
            # Include minimal table info without the full data
            if data_tables:
                table_info = []
                for table in data_tables:
                    table_info.append({
                        "title": table.get("title", "Untitled"),
                        "columns": len(table.get("columns", [])),
                        "rows": len(table.get("rows", [])),
                        "included": True
                    })
                result["data_tables"] = table_info
                
            # Log success message
            self.logger.info(f"Successfully generated PDF: {output_path}")
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating PDF: {str(e)}")
            # Return error result
            return {
                "status": "error",
                "message": f"Failed to generate PDF: {str(e)}",
                "error": str(e)
            }
    
    def _open_pdf(self, pdf_path: str) -> None:
        """
        Open the PDF file using the appropriate system command.
        
        Args:
            pdf_path (str): Path to the PDF file
        """
        try:
            # Check if pdf_path exists
            if not os.path.exists(pdf_path):
                self.logger.warning(f"Cannot open PDF - file does not exist: {pdf_path}")
                return
                
            if os.name == 'nt':  # Windows
                os.startfile(pdf_path)
            elif os.name == 'posix':  # macOS or Linux
                platform = os.uname().sysname
                if platform == 'Darwin':  # macOS
                    subprocess.Popen(['open', pdf_path])
                else:  # Linux
                    subprocess.Popen(['xdg-open', pdf_path])
            else:
                self.logger.warning(f"Unsupported operating system for auto-opening PDF: {os.name}")
        except Exception as e:
            self.logger.warning(f"Error opening PDF file: {str(e)}")


def create_pdf_generator_from_input(input_data: GenerateDocumentInput) -> Dict[str, Any]:
    """
    Create a PDF from the GenerateDocumentInput.
    
    Args:
        input_data (GenerateDocumentInput): Input data for document generation
        
    Returns:
        Dict[str, Any]: Dictionary containing path to the generated PDF file and additional information
    """
    tool = PDFGeneratorTool()
    return tool.run(
        content=input_data.content,
        output_path=input_data.output_path,
        title=input_data.title,
        metadata=input_data.metadata,
        visualizations=input_data.visualizations,
        data_tables=input_data.data_tables,
        options=input_data.options.dict() if input_data.options else None,
        format=input_data.format.value if hasattr(input_data, 'format') else None,
        # Add compatibility with any other fields that might be present
        **{k: v for k, v in input_data.__dict__.items() if k not in [
            'content', 'output_path', 'title', 'metadata', 'visualizations', 
            'data_tables', 'options', 'format'
        ] and not k.startswith('_')}
    )
