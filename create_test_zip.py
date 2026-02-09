import shutil
import os

os.makedirs("temp_mkdocs_project/docs", exist_ok=True)
with open("temp_mkdocs_project/mkdocs.yml", "w") as f:
    f.write("site_name: Test Zip Project")
with open("temp_mkdocs_project/docs/index.md", "w") as f:
    f.write("# Hello from Zip\n\nThis site was uploaded as a zip file.")

shutil.make_archive("test_mkdocs", 'zip', "temp_mkdocs_project")
print("Created test_mkdocs.zip")
