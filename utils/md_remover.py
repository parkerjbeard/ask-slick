def remove_markdown(text):
    # Remove bold formatting
    text = text.replace('**', '')
    
    # Remove italic formatting
    text = text.replace('*', '')
    text = text.replace('_', '')
    
    # Remove bullet points
    text = text.replace('- ', '')
    
    # Replace numbered lists with simple numbers followed by a period
    import re
    text = re.sub(r'^(\d+)\.\s', r'\1. ', text, flags=re.MULTILINE)
    
    return text