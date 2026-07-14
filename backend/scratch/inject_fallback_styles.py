"""
Inject a minimal Tailwind CDN offline fallback <style> block into every
manager/ and employee/ HTML file that loads from cdn.tailwindcss.com.

The block is inserted immediately after the Tailwind <script> tag so it
only activates when CDN classes are missing.
"""

import os, re

ROOT = r"c:\Users\anwar\Downloads\agripulse-v2-structure (3)\trial\frontend"

FALLBACK_STYLE = """\
  <style>
    /* Tailwind CDN offline fallback — basic readable layout */
    *, *::before, *::after { box-sizing: border-box; }
    html, body {
      margin: 0;
      padding: 0;
      min-height: 100vh;
      background-color: #f8f9ff;
      color: #0b1c30;
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      line-height: 1.5;
    }
    img { max-width: 100%; }
    a { color: #ea580c; }
    a:hover { text-decoration: underline; }
    button, input, select, textarea {
      font: inherit;
    }
    input[type="text"], input[type="password"], input[type="email"],
    input[type="number"], select, textarea {
      width: 100%;
      border: 1px solid #bfc9c3;
      border-radius: 6px;
      padding: 8px 12px;
      background: #ffffff;
      color: #0b1c30;
    }
    button {
      cursor: pointer;
      border: none;
      border-radius: 6px;
      padding: 8px 16px;
      background-color: #7c2d12;
      color: #ffffff;
      font-weight: 600;
    }
    button:hover { background-color: #9a3412; }
    table { border-collapse: collapse; width: 100%; }
    th, td { padding: 8px 12px; border: 1px solid #e5e7eb; text-align: left; }
    th { background-color: #f1f5f9; font-weight: 700; }
  </style>"""

# Pattern matches the Tailwind CDN script tag (with or without ?plugins=...)
CDN_PATTERN = re.compile(
    r'(<script\s+src="https://cdn\.tailwindcss\.com[^"]*"\s*>\s*</script>)'
)

updated = []
skipped = []

for portal in ("manager", "employee"):
    portal_dir = os.path.join(ROOT, portal)
    for fname in sorted(os.listdir(portal_dir)):
        if not fname.endswith(".html"):
            continue
        path = os.path.join(portal_dir, fname)
        with open(path, "r", encoding="utf-8") as f:
            original = f.read()

        # Skip if fallback already present
        if "Tailwind CDN offline fallback" in original:
            skipped.append(f"{portal}/{fname}")
            continue

        # Inject after the CDN script tag
        new, count = CDN_PATTERN.subn(
            r"\1\n" + FALLBACK_STYLE,
            original,
            count=1,
        )
        if count:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
            updated.append(f"{portal}/{fname}")
        else:
            skipped.append(f"{portal}/{fname} (no CDN tag found)")

print(f"Updated {len(updated)} files:")
for f in updated:
    print(f"  + {f}")
if skipped:
    print(f"\nSkipped {len(skipped)} files (already patched or no tag):")
    for f in skipped:
        print(f"  - {f}")
