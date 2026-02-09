const simpleGit = require('simple-git');
const path = require('path');
const fs = require('fs');
const { exec } = require('child_process');
const { v4: uuidv4 } = require('uuid');

const TEMP_DIR = path.join(__dirname, '../../temp_repos');
const DOCS_DIR = path.join(__dirname, '../../public/docs');

// Ensure directories exist
if (!fs.existsSync(TEMP_DIR)) fs.mkdirSync(TEMP_DIR, { recursive: true });
if (!fs.existsSync(DOCS_DIR)) fs.mkdirSync(DOCS_DIR, { recursive: true });

exports.cloneRepository = async (repoUrl, branch = 'main') => {
    const repoId = uuidv4();
    const repoPath = path.join(TEMP_DIR, repoId);

    console.log(`Cloning ${repoUrl} (branch: ${branch}) to ${repoPath}...`);
    try {
        await simpleGit().clone(repoUrl, repoPath, ['--branch', branch, '--single-branch']);
        return { repoId, repoPath };
    } catch (error) {
        console.error('Git clone failed:', error);
        if (fs.existsSync(repoPath)) {
            fs.rmSync(repoPath, { recursive: true, force: true });
        }
        throw error;
    }
};

exports.processMkDocs = async (repoPath, repoId) => {
    const mkdocsPath = path.join(repoPath, 'mkdocs.yml');
    if (!fs.existsSync(mkdocsPath)) {
        throw new Error('Not an MkDocs repository (mkdocs.yml not found)');
    }

    // 1. Install Dependencies (if requirements.txt exists)
    const requirementsPath = path.join(repoPath, 'requirements.txt');
    if (fs.existsSync(requirementsPath)) {
        console.log(`Found requirements.txt, installing dependencies...`);
        try {
            await new Promise((resolve, reject) => {
                exec(`pip3 install -r requirements.txt --break-system-packages`, { cwd: repoPath }, (error, stdout, stderr) => {
                    if (error) {
                        console.error(`Pip install error: ${error.message}`);
                        console.error(`Stderr: ${stderr}`);
                        // fail soft? or hard? Let's fail hard for now as the build will likely fail anyway.
                        return reject(error);
                    }
                    console.log(`Pip install output: ${stdout}`);
                    resolve();
                });
            });
        } catch (pipError) {
            console.error('Failed to install dependencies:', pipError);
            throw new Error(`Failed to install python dependencies: ${pipError.message}`);
        }
    }

    // 2. Inject site_url for sub-path hosting
    // We need to read mkdocs.yml, check if site_url is set, and if not (or even if it is to match our hosting), update it.
    // However, parsing YAML safely requires a library. Let's do a simple regex replacement or append if simple, 
    // BUT modifying the file is safer with a parser.
    // For now, let's append/overwrite `site_url` using a simple file append if simpler, or use `js-yaml` if available.
    // `js-yaml` is not in package.json. Let's install it or use string manipulation for now to avoid extra deps if possible.
    // Actually, appending "site_url: /docs/repoId/" to the end might override previous values in valid YAML? 
    // YAML doesn't support duplicate keys well.
    // Better approach: Use environment variable or command line arg? 
    // `mkdocs build` doesn't strictly support overriding config via CLI args for all properties.
    // Let's safe-bet: Read file, replace `site_url: ...` or append it.

    // Let's rely on simple text processing for now to avoid new deps if we can, but `js-yaml` is safer.
    // User wants "link system".
    // Let's try to append `site_url: /docs/${repoId}/` to end of file. Most parsers use the last occurrence.
    const siteUrlConfig = `\nsite_url: /docs/${repoId}/\n`;
    fs.appendFileSync(mkdocsPath, siteUrlConfig);
    console.log(`Injected site_url: /docs/${repoId}/ into mkdocs.yml`);

    const outputPath = path.join(DOCS_DIR, repoId);
    console.log(`Building MkDocs for ${repoId} to ${outputPath}...`);

    return new Promise((resolve, reject) => {
        // Determine the build command. We use 'mkdocs' assuming it's in the PATH (installed within Docker).
        // If running locally, mkdocs must be installed.
        console.log(`Executing python3 -m mkdocs build in ${repoPath}`);
        exec(`python3 -m mkdocs build -d "${outputPath}" -v`, { cwd: repoPath }, (error, stdout, stderr) => {
            if (error) {
                console.error(`MkDocs build error: ${error.message}`);
                console.error(`Stderr: ${stderr}`);
                return reject(error);
            }
            console.log(`MkDocs build output: ${stdout}`);

            // Clean up temp repo after successful build
            try {
                console.log(`Cleaning up temp repo: ${repoPath}`);
                fs.rmSync(repoPath, { recursive: true, force: true });
            } catch (cleanupError) {
                console.warn('Failed to cleanup temp repo:', cleanupError);
            }

            resolve({ outputPath, relativePath: `/docs/${repoId}` });
        });
    });
};
