#!/usr/bin/env python3
"""
Test script for QA Engine
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from qa.qa_engine import engine

def test_qa():
    # Use one of the existing PDFs
    pdf_path = 'uploads/e5826567-7bcc-4db0-b823-39e5c93d9d74_sample_document_qa.pdf'
    if not os.path.exists(pdf_path):
        print("PDF not found")
        return

    doc_id = 'test_doc'
    try:
        print("Processing document...")
        stats = engine.process_document(pdf_path, doc_id)
        print(f"Processed: {stats}")

        print("Asking question...")
        result = engine.answer(doc_id, "What is this document about?")
        print(f"Answer: {result['answer']}")
        print(f"Confidence: {result['confidence']}%")
        print("Sources:")
        for src in result['sources']:
            print(f"  - {src['text'][:100]}... (sim: {src['similarity']})")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test_qa()