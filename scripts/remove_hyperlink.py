import docx

def remove_github_links(filepath):
    try:
        doc = docx.Document(filepath)
        changed = False
        
        # Check standard hyperlinks in relationships
        for rel in doc.part.rels.values():
            if "hyperlink" in rel.reltype:
                if "github.com" in rel.target_ref.lower():
                    rel._target = "#"
                    changed = True
                    print(f"Removed hyperlink in {filepath}")
                    
        if changed:
            doc.save(filepath)
            print(f"Successfully updated {filepath}")
        else:
            print(f"No github links found to remove in {filepath}")
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

remove_github_links('docs/CAPSTONE_SUBMISSION_REPORT.docx')
remove_github_links('docs/Capstone_Submission_Knowledge_Assistant.docx')
