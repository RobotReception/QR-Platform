import os

def resolve_font_file(filename: str, fonts_dir: str = "fonts") -> str:
    filename = os.path.basename(filename)
    if not filename.lower().endswith((".ttf", ".otf")):
        return "Invalid extension"
        
    base, ext = os.path.splitext(filename)
    safe_base = "".join(c for c in base if c.isalnum() or c in ("-", "_")).strip()
    if not safe_base:
        safe_base = "uploaded_font"
    normalized_filename = f"{safe_base}{ext.lower()}"
    
    path = os.path.join(fonts_dir, normalized_filename)
    if os.path.exists(path):
        return path
        
    # Smart fallbacks
    if os.path.exists(fonts_dir):
        # 1. Case-insensitive exact match
        target_lower = normalized_filename.lower()
        for file in os.listdir(fonts_dir):
            if file.lower() == target_lower:
                return os.path.join(fonts_dir, file)
                
        # 2. Family-based matching
        # Strip common weight suffixes to get the core family name
        family = safe_base
        suffixes = ("-Regular", "-Bold", "-Italic", "-Light", "-Medium", "-SemiBold", "-ExtraBold", "-Thin")
        for suffix in suffixes:
            if family.lower().endswith(suffix.lower()):
                family = family[:-len(suffix)]
                break
                
        # Normalize family name
        family_lower = family.lower()
        
        # Look for files matching the family name
        candidates = []
        for file in os.listdir(fonts_dir):
            if not file.lower().endswith(ext.lower()):
                continue
            file_base = os.path.splitext(file)[0].lower()
            if file_base == family_lower or file_base.startswith(family_lower + "-") or file_base.startswith(family_lower + "_"):
                candidates.append(file)
                
        if candidates:
            # If the original request wanted bold, prefer bold candidates
            is_bold_req = any(x in safe_base.lower() for x in ("bold", "semibold", "extrabold"))
            if is_bold_req:
                bold_candidates = [c for c in candidates if "bold" in c.lower()]
                if bold_candidates:
                    return os.path.join(fonts_dir, bold_candidates[0])
            else:
                # Prefer regular/normal candidates
                regular_candidates = [c for c in candidates if "regular" in c.lower() or "normal" in c.lower()]
                if regular_candidates:
                    return os.path.join(fonts_dir, regular_candidates[0])
                    
            # Fallback to the first candidate found
            return os.path.join(fonts_dir, candidates[0])
            
    return "Not Found"

# Run tests
print("Cairo.ttf ->", resolve_font_file("Cairo.ttf", "fonts"))
print("Cairo-Bold.ttf ->", resolve_font_file("Cairo-Bold.ttf", "fonts"))
print("alfont_com_29LTZaridSlab-Medium-1-Bold.ttf ->", resolve_font_file("alfont_com_29LTZaridSlab-Medium-1-Bold.ttf", "fonts"))
print("alfont_com_Zain-PC-VF-Regular.ttf ->", resolve_font_file("alfont_com_Zain-PC-VF-Regular.ttf", "fonts"))
