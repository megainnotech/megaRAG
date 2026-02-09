
# Create a dummy MkDocs project structure
mkdir -p temp_mkdocs_project
echo "site_name: Test Zip Project" > temp_mkdocs_project/mkdocs.yml
echo "# Hello from Zip" > temp_mkdocs_project/index.md

# Zip it
# Windows might not have 'zip' command. 
# We'll use python to create zip.
