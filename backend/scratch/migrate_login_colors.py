import os
import difflib

file_path = r"c:\Users\anwar\Downloads\agripulse-v2-structure (3)\trial\frontend\login.html"

with open(file_path, "r", encoding="utf-8") as f:
    original_lines = f.readlines()

original_text = "".join(original_lines)

# Perform replacements
modified_text = original_text

# 1. Colors
modified_text = modified_text.replace("#003527", "#7c2d12")
modified_text = modified_text.replace("#004d39", "#9a3412")
modified_text = modified_text.replace("#006c49", "#ea580c")

# 2. Tailwind class strings
modified_text = modified_text.replace("shadow-emerald-950/20", "shadow-orange-950/20")
modified_text = modified_text.replace("bg-emerald-400", "bg-orange-400")
modified_text = modified_text.replace("bg-emerald-500", "bg-orange-500")
modified_text = modified_text.replace("text-emerald-300", "text-orange-300")
modified_text = modified_text.replace("text-emerald-700/80", "text-orange-700/80")
modified_text = modified_text.replace("text-emerald-500", "text-orange-500")

# Write back
with open(file_path, "w", encoding="utf-8") as f:
    f.write(modified_text)

modified_lines = modified_text.splitlines(keepends=True)

# Generate diff
diff = difflib.unified_diff(
    original_lines,
    modified_lines,
    fromfile="original/login.html",
    tofile="modified/login.html"
)

print("".join(diff))
