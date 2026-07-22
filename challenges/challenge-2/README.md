# Challenge 2: Document Processing and Vectorized Search

**Expected Duration:** 60 minutes

## Introduction
Welcome to Challenge 2! In this challenge, you'll build a comprehensive document processing and search system using Azure AI services. This foundational challenge demonstrates how to process insurance documents (both text and images), create vectorized search capabilities, and prepare the knowledge base that will power all subsequent AI agent implementations.

## What are we building?
In this challenge, we will create a complete document processing and vectorized search system that forms the backbone of our insurance AI agent ecosystem:

- **Document Upload System**: Azure Blob Storage integration for secure document management
- **Multimodal Processing Pipeline**: Foundry-hosted LLM powered text and image processing capabilities  
- **OCR Extraction System**: Advanced text extraction from insurance claim images
- **Vectorized Search Index**: Azure AI Search with integrated vectorization for semantic search
- **Hybrid Search Capabilities**: Combined keyword, vector, and semantic search functionality

This system will serve as the knowledge foundation for all agents in subsequent challenges, enabling them to access and query insurance policies, claims, and statements intelligently.

## Data Structure Overview

Your challenge includes comprehensive insurance data across three categories:

| Data Category | Files | Purpose |
|---------------|-------|---------|
| **Claims Data** (`data/images/`) | `crash1.jpg`, `crash2.jpg`, `crash3.jpg`, `crash4.jpg`, `crash5.jpg` | Vehicle accident documentation for OCR processing |
| **Policy Data** (`data/policies/`) | `commercial_auto_policy.md`, `comprehensive_auto_policy.md`, `high_value_vehicle_policy.md`, `liability_only_policy.md`, `motorcycle_policy.md` | Insurance policy documents for text processing and policy validation |
| **Claim Statements** (`data/statements/`) | `crash1_front.jpeg`, `crash1_back.jpeg`, `crash2_front.jpeg`, `crash2_back.jpeg`, `crash3_front.jpeg`, `crash3_back.jpeg`, `crash4_front.jpeg`, `crash4_back.jpeg`, `crash5_front.jpeg`, `crash5_back.jpeg` | Written statements (front and back) corresponding to each claim for comprehensive analysis |


## Document Processing after the Generative AI Wave

Generative AI has transformed document processing from rigid template-based systems to intelligent, understanding-based approaches. Modern models process text, images, and complex layouts simultaneously, eliminating separate pipelines for different content types.

**Key Advantages:**
- Context-aware extraction without predefined templates
- Unified processing of multimodal content (text, images, tables)
- Natural language queries instead of fixed extraction fields
- Minimal training requirements using pre-trained foundation models

**For Insurance:** Complex documents—policies, claim photos, handwritten statements, invoices—can now be processed in a single pipeline, understanding both textual terms and visual damage assessments together.

When building document processing systems today, selecting the right AI models is crucial for achieving accurate and efficient results. Here are the primary options available for processing insurance documents:

### <img src="images/mistral-logo.png" alt="Mistral" width="30" height="30" style="vertical-align: middle;">  Mistral Document AI 

Mistral's specialized [document AI models](https://docs.mistral.ai/capabilities/document_ai) provide efficient document understanding capabilities:
- Optimized for document structure recognition
- Strong performance on text extraction and classification
- Cost-effective alternative for text-heavy documents
- Support for multiple document formats and layouts
- Fast inference times for batch processing scenarios

**Why Choose Mistral:**
- **Up to 3x faster** inference times compared to general-purpose LLMs for document tasks
- **40-60% cost savings** on high-volume document processing workloads
- **Native multilingual support** with 100+ languages out-of-the-box
- **99%+ accuracy** on structured document extraction tasks
- **Scalable throughput** handling 1000+ documents per minute

Mistral Document AI is particularly well-suited for scenarios where you need to process large volumes of textual documents efficiently while maintaining high accuracy and controlling costs.

### <img src="images/azure-document-intelligence-logo.png" alt="Azure Document Intelligence" width="30" height="30" style="vertical-align: middle;"> Azure Document Intelligence

[Azure Document Intelligence](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/?view=doc-intel-4.0.0) (formerly Form Recognizer) is an AI service that provides advanced document processing capabilities using multimodal foundation models. Unlike traditional OCR tools, Document Intelligence uses machine learning to understand documents in a more comprehensive way:

- **Prebuilt Models**: Ready-to-use models for invoices, receipts, ID cards, insurance documents, and other common forms
- **Custom Models**: Train models on your specific document types for tailored extraction accuracy
- **Layout Analysis**: Understand document structure including tables, paragraphs, selection marks, and document hierarchy
- **Key-Value Extraction**: Automatically identify and extract field-label pairs from forms
- **Multi-Page Support**: Process complex multi-page documents with sophisticated layout understanding
- **High Accuracy OCR**: Extract printed and handwritten text with high precision across multiple languages
- **Azure Integration**: Native integration with Azure AI services, security, compliance, and Azure AI Search

Azure Document Intelligence is particularly powerful for insurance scenarios where structured forms (claims, policies) and unstructured documents (handwritten statements, accident reports) need to be processed together. Its prebuilt insurance document models can extract policy numbers, claim amounts, dates, and other critical fields automatically.



### <img src="images/openai-logo.png" alt="Multimodal Models" width="30" height="30" style="vertical-align: middle;"> Multimodal Models

**Foundry-hosted LLM**
A powerful multimodal model that can process both text and images with high accuracy. This model excels at:
- Understanding complex document layouts and formatting
- Extracting structured information from unstructured documents
- Processing insurance claim images and photos
- Performing optical character recognition (OCR) on documents
- Analyzing visual content alongside textual information

Foundry-hosted LLMs offer an excellent balance between cost, speed, and performance for document processing tasks, making them ideal for processing both policy documents and visual claim evidence.

## Task 1 - Statement Processing with Multiple AI Approaches 
The `statements_processing` folder contains advanced examples showcasing different AI approaches for processing insurance claim statements. This section demonstrates how to choose and implement the right model for your specific use case. It will also generate the markdown files needed for vectorization in the next part of the challenge:

**GPT Statement Processing (`gpt_statement_processing.py`)**
- Uses a Foundry-hosted LLM for intelligent statement analysis
- Excels at understanding context and extracting nuanced information
- Ideal for complex, unstructured claim narratives
- Provides high-quality extraction with natural language understanding

**Mistral Document Intelligence (`mistral_doc_intelligence.py`)**
- Leverages Mistral's specialized document AI models
- Optimized for structured document processing at scale
- Cost-effective for high-volume statement processing
- Fast inference times for batch operations

**Azure Document Intelligence Integration**
- Demonstrates prebuilt models for form and document extraction
- Shows custom model training for insurance-specific documents
- Provides layout analysis and key-value pair extraction
- Ideal for standardized forms and structured statements

This comparison helps you understand when to use each approach based on document type, volume, complexity, and cost considerations. Review the implementations to see practical examples of model selection and integration strategies.

## Task 2 - Image and Claims Processing
> **Note:** You must run mistral_doc_intelligence.py before starting this part or copy the contents of the `examples/mistral` folder to `./output/mistral`.

Time to extract information from claim images! Please navigate to `scripts/imageprocessing.ipynb` for a detailed implementation of:
- Processing insurance claim photos and accident documentation
- Extracting text from images using Foundry-hosted vision model capabilities
- Performing OCR on handwritten statements and invoices
- Structuring extracted data for vectorization
- Integrating visual claim evidence into Azure AI Search

This notebook showcases multimodal AI processing techniques for analyzing damage photos and extracting critical claim information from visual content.

## Task 3 - Policy Document Processing

Time to process your insurance policy documents! Please navigate to `scripts/policiesprocessing.ipynb` for a comprehensive walkthrough on:
- Setting up Azure Blob Storage for document management
- Processing text-based policy documents using a Foundry-hosted LLM
- Extracting structured information from policy markdown files
- Creating vectorized embeddings for semantic search
- Uploading processed documents to Azure AI Search

This notebook demonstrates how to transform unstructured policy text into a searchable knowledge base that agents can query intelligently.

Great! If you are finished and ready for extra challenges, there's much more to explore!

## Task 4 (optional) - Explore the Full Potential of Mistral Models

Mistral AI offers powerful document understanding capabilities through **Data Annotations** - a feature that enables structured data extraction with precise location information (bounding boxes) for each extracted field.

### What are Data Annotations?

Data Annotations in Mistral Document AI allow you to:

| Feature | Description |
|---------|-------------|
| **Structured Extraction** | Define JSON schemas to extract specific fields from documents |
| **Bounding Boxes** | Get precise coordinates showing where each field was found on the page |
| **Visual Verification** | Highlight extracted regions for human review and validation |
| **Confidence Scores** | Receive confidence levels for each extracted field |
| **Multi-page Support** | Process complex documents with page-level annotations |

### Why Use Data Annotations for Insurance Claims?

In insurance claim processing, knowing *where* information came from is just as important as *what* was extracted:

1. **Audit Trail**: Bounding boxes provide visual proof of where data originated
2. **Fraud Detection**: Verify that signatures, dates, and amounts match their expected locations
3. **Human-in-the-Loop**: Enable reviewers to quickly verify AI extractions
4. **Regulatory Compliance**: Maintain traceable data lineage for compliance requirements

### Implementation Example

Navigate to `statements_processing/mistral_doc_intel_annotations.py` for a comprehensive implementation that demonstrates:

```python
# Define a schema for structured extraction
CLAIM_STATEMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "claimant_name": {"type": "string", "description": "Full name of claimant"},
        "policy_number": {"type": "string", "description": "Insurance policy number"},
        "incident_description": {"type": "string", "description": "What happened"},
        "damage_description": {"type": "string", "description": "Damage details"},
        "signature_present": {"type": "boolean", "description": "Is signature present"}
    }
}

# Extract with bounding box annotations
result = extract_with_annotations(
    file_path="claim_form.pdf",
    json_schema=CLAIM_STATEMENT_SCHEMA,
    include_bboxes=True
)

# Each field includes its location on the document
for annotation in result['annotations']:
    print(f"Field: {annotation.field_name}")
    print(f"Value: {annotation.value}")
    print(f"Location: Page {annotation.bbox.page}, ({annotation.bbox.x_min}, {annotation.bbox.y_min})")
```

### Key Functions in the Implementation

| Function | Purpose |
|----------|---------|
| `extract_with_annotations()` | Core extraction with JSON schema and bounding boxes |
| `extract_claim_statement()` | Pre-configured for insurance claim forms |
| `extract_damage_assessment()` | Specialized for vehicle damage analysis |
| `batch_extract_with_annotations()` | Process multiple documents concurrently |
| `visualize_annotations()` | Generate visual overlay of extracted fields |
| `export_annotations_to_json()` | Save results with full annotation data |

### Running the Demo

```bash
cd challenge-1/statements_processing
python mistral_doc_intel_annotations.py ../../challenge-1/data/statements/crash1_front.jpeg
```

This will process the claim statement, extract structured data with annotations, and export the results to a JSON file showing the exact location of each extracted field.

### Learn More

- [Mistral Document AI Documentation](https://docs.mistral.ai/capabilities/document_ai)
- [JSON Schema for Structured Extraction](https://docs.mistral.ai/capabilities/document_ai/#structured-extraction)
- [Bounding Box Annotations Guide](https://docs.mistral.ai/capabilities/document_ai/#annotations)

## 🎯 Conclusion

Congratulations! You've successfully built a comprehensive document processing and vectorized search system that serves as the foundation for intelligent AI agents. 

**Key Achievements:**
- Processed insurance policy documents and created searchable embeddings with Azure AI Search
- Extracted information from claim images using Foundry-hosted multimodal capabilities
- Implemented hybrid search combining keyword, vector, and semantic ranking
- Explored multiple AI approaches (GPT, Mistral, Azure Document Intelligence) for different use cases
- Established a knowledge base that AI agents can query using natural language

**What You Built:**
Your system now intelligently processes text policies, claim photos, and statements—transforming unstructured insurance documents into a queryable knowledge corpus. This infrastructure enables the AI agents you'll build in Challenge 3 to access policy terms, analyze claim evidence, and make informed decisions.

**Next Challenge:**
In Challenge 3, you'll build an AI agent that leverages this document processing foundation to autonomously orchestrate claims assessment workflows. Ready to continue? Head to [Challenge 3](../challenge-3/README.md)!