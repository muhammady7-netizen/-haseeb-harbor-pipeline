try:
    from docx import Document
    doc = Document(r"C:\Users\Haseeb Mirza\Downloads\task-approach-guide-updated.docx")
    for i, para in enumerate(doc.paragraphs):
        if para.text.strip():
            print(para.text.strip())
        if i > 200:
            print("... (truncated)")
            break
except ImportError:
    print("python-docx not installed, skipping")
except Exception as e:
    print(f"Error: {e}")
