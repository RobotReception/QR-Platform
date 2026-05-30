import sys, zipfile, xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')

# .xlsx is a ZIP file containing XML sheets
# Parse it manually without openpyxl
path = r"D:\QR\test_guests.xlsx"

with zipfile.ZipFile(path, 'r') as z:
    # Read shared strings
    shared_strings = []
    if 'xl/sharedStrings.xml' in z.namelist():
        tree = ET.parse(z.open('xl/sharedStrings.xml'))
        ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        for si in tree.findall('.//s:si', ns):
            texts = si.findall('.//s:t', ns)
            shared_strings.append(''.join(t.text or '' for t in texts))

    # List sheets
    print(f"Files in xlsx: {[n for n in z.namelist() if 'sheet' in n.lower()]}")
    print(f"Shared strings ({len(shared_strings)}): {shared_strings[:30]}")
    print()

    # Read sheet1
    for sheet_file in ['xl/worksheets/sheet1.xml']:
        if sheet_file not in z.namelist():
            continue
        tree = ET.parse(z.open(sheet_file))
        ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        rows = tree.findall('.//s:row', ns)
        print(f"=== {sheet_file} ({len(rows)} rows) ===")
        for row in rows[:15]:  # First 15 roزws
            cells = []
            for c in row.findall('s:c', ns):
                ref = c.get('r', '')
                t = c.get('t', '')  # 's' = shared string, 'n' = number
                v = c.find('s:v', ns)
                val = v.text if v is not None else ''
                if t == 's' and val.isdigit():
                    idx = int(val)
                    val = shared_strings[idx] if idx < len(shared_strings) else val
                cells.append(val)
            print(f"  Row {row.get('r')}: {cells}")
        print()
