const db = require('../config/db');
const gitService = require('../services/gitService');
const ragService = require('../services/ragService');
const Document = db.Document;
const path = require('path');
const fs = require('fs');

exports.createGitDocument = async (req, res) => {
    try {
        const { url, branch, tags } = req.body;
        if (!url) {
            return res.status(400).json({ message: 'Git URL is required' });
        }

        // 1. Clone Repo
        const { repoId, repoPath } = await gitService.cloneRepository(url, branch || 'main');

        // 2. Process MkDocs (Build)
        try {
            await gitService.processMkDocs(repoPath, repoId);
        } catch (err) {
            return res.status(400).json({ message: 'Failed to process MkDocs project', error: err.message });
        }

        // 3. Save to DB
        const document = await Document.create({
            title: url.split('/').pop().replace('.git', '') || 'Untitled Git Repo',
            type: 'git',
            sourceUrl: url,
            localPath: `/docs/${repoId}`, // Served via static middleware
            tags: tags || {},
            branch: branch || 'main'
        });

        res.status(201).json(document);
    } catch (error) {
        console.error('Create Git Doc Error:', error);
        res.status(500).json({ message: 'Internal Server Error', error: error.message });
    }
};

const AdmZip = require('adm-zip');

exports.createFileDocument = async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ message: 'No file uploaded' });
        }

        const { tags } = req.body;
        const parsedTags = tags ? JSON.parse(tags) : {};
        let documentData = {
            title: req.file.originalname,
            type: 'file',
            localPath: `/files/${req.file.filename}`,
            tags: parsedTags
        };

        // Connect to existing gitService logic if it's a zip
        if (req.file.mimetype.includes('zip') || req.file.originalname.endsWith('.zip')) {
            const zipPath = req.file.path;
            const zip = new AdmZip(zipPath);
            const zipEntries = zip.getEntries();

            // simple check for mkdocs.yml
            const mkdocsEntry = zipEntries.find(entry => entry.entryName === 'mkdocs.yml' || entry.entryName.endsWith('/mkdocs.yml'));

            if (mkdocsEntry) {
                console.log('MkDocs project detected in zip upload.');

                // Extract to a temp directory to build
                // We reuse gitService.processMkDocs which expects a folder path
                const { v4: uuidv4 } = require('uuid');
                const extractId = uuidv4();
                const extractPath = path.join(__dirname, '../../temp_repos', extractId);

                console.log(`Extracting zip to ${extractPath}`);
                if (!fs.existsSync(extractPath)) fs.mkdirSync(extractPath, { recursive: true });

                try {
                    zip.extractAllTo(extractPath, true);
                    console.log('Zip extraction complete.');
                } catch (extractError) {
                    console.error('Zip extraction failed:', extractError);
                    throw extractError;
                }

                // Check if mkdocs.yml is in root or subfolder
                // gitService.processMkDocs expects repoPath. 
                // If mkdocs.yml is inside a folder in the zip, we need to point to that folder.
                let buildPath = extractPath;
                if (mkdocsEntry.entryName.includes('/')) {
                    // It's nested. Let's find the directory containing mkdocs.yml
                    // Simple assumption: if entry is "folder/mkdocs.yml", buildPath is extractPath/folder
                    const pathParts = mkdocsEntry.entryName.split('/');
                    pathParts.pop(); // remove mkdocs.yml
                    if (pathParts.length > 0) {
                        buildPath = path.join(extractPath, pathParts.join('/'));
                    }
                }
                console.log(`Build path determined as: ${buildPath}`);

                try {
                    // Reuse the repoId logic from processMkDocs, or pass one? 
                    // processMkDocs(repoPath, repoId) -> builds to public/docs/repoId
                    // We'll use extractId as the "repoId" for the served docs
                    console.log(`Calling gitService.processMkDocs(${buildPath}, ${extractId})`);
                    await gitService.processMkDocs(buildPath, extractId);
                    console.log('MkDocs build complete.');

                    // Update document data to point to the served site
                    documentData.type = 'git'; // Treat as git/site type
                    documentData.localPath = `/docs/${extractId}`;
                    documentData.title = req.file.originalname.replace('.zip', '') + ' (Uploaded)';

                    // Cleanup zip file? Maybe keep it as "source"? 
                    // For now, let's keep the zip file in 'files' as backup/source, 
                    // but the document entry points to the site.
                } catch (buildError) {
                    console.error('Failed to build MkDocs from zip:', buildError);
                    // Fallback: treated as normal file if build fails? 
                    // Or return error? User said "if yes, place in subfolder".
                    // I'll return error to inform user it failed to build.
                    return res.status(400).json({ message: 'MkDocs build failed', error: buildError.message });
                } finally {
                    // We DO NOT clean up the extracted folder here because the RAG service needs it.
                    // It will remain in temp_repos for ingestion.
                    console.log(`Keeping extracted path for RAG: ${extractPath}`);
                }
            }
        }

        const document = await Document.create(documentData);

        res.status(201).json(document);
    } catch (error) {
        console.error('Create File Doc Error:', error);
        res.status(500).json({ message: 'Internal Server Error', error: error.message });
    }
};

exports.getAllDocuments = async (req, res) => {
    try {
        const { search, tags, operator } = req.query; // operator: 'AND' | 'OR'
        const { Op } = db.Sequelize;
        let whereClause = {};

        // 1. Full-text search on title (case-insensitive)
        if (search) {
            whereClause.title = { [Op.iLike]: `%${search}%` };
        }

        // 2. Tag Filtering with AND/OR Logic
        if (tags) {
            // tags expected format: "key:value,key2:value2"
            const tagPairs = tags.split(',');
            const condition = operator === 'OR' ? Op.or : Op.and;

            const tagConditions = tagPairs.map(pair => {
                const [key, value] = pair.split(':');
                if (key && value) {
                    // Check if key exists and value matches in JSONB
                    // Construct: { tags: { [Op.contains]: { [key]: value } } }
                    return { tags: { [Op.contains]: { [key]: value } } };
                }
                return null; // Invalid pair
            }).filter(Boolean);

            if (tagConditions.length > 0) {
                if (operator === 'OR') {
                    whereClause[Op.or] = tagConditions;
                } else {
                    // For AND, we can merge into a single contains object or array of contains
                    // { tags: { [Op.contains]: mergedObject } } is cleaner for JSONB
                    const mergedTags = {};
                    tagPairs.forEach(pair => {
                        const [key, value] = pair.split(':');
                        if (key && value) mergedTags[key] = value;
                    });
                    whereClause.tags = { [Op.contains]: mergedTags };
                }
            }
        }

        const documents = await Document.findAll({
            where: whereClause,
            order: [['createdAt', 'DESC']]
        });
        res.json(documents);
    } catch (error) {
        console.error('Search Error:', error);
        res.status(500).json({ message: 'Internal Server Error', error: error.message });
    }
};

exports.deleteDocument = async (req, res) => {
    try {
        const { id } = req.params;
        const document = await Document.findByPk(id);

        if (!document) {
            return res.status(404).json({ message: 'Document not found' });
        }

        // Resolve absolute path
        const absolutePath = path.join(__dirname, '../../public', document.localPath);
        console.log(`Deleting document path: ${absolutePath}`);

        if (fs.existsSync(absolutePath)) {
            const stat = fs.statSync(absolutePath);
            if (stat.isDirectory()) {
                fs.rmSync(absolutePath, { recursive: true, force: true });
            } else {
                fs.unlinkSync(absolutePath);
            }
        }

        // Cleanup RAG
        await ragService.deleteDocument(id);

        await document.destroy();
        res.json({ message: 'Document deleted' });
    } catch (error) {
        res.status(500).json({ message: 'Internal Server Error', error: error.message });
    }
};

exports.processDocument = async (req, res) => {
    try {
        const { id } = req.params;
        const document = await Document.findByPk(id);

        if (!document) {
            return res.status(404).json({ message: 'Document not found' });
        }

        // Update status
        document.ragStatus = 'processing';
        await document.save();

        // Determine correct path for RAG
        // If git, we need the repoId (folder name in temp_repos)
        // localPath is like /docs/{repoId}
        let ragLocalPath = document.localPath;
        if (document.type === 'git') {
            ragLocalPath = document.localPath.replace('/docs/', '');
        }

        // Trigger RAG Ingestion (Async)
        ragService.ingestDocument(document.id, document.type, ragLocalPath, document.tags)
            .then(async () => {
                document.ragStatus = 'indexed';
                await document.save();
            })
            .catch(async (err) => {
                console.error('RAG Ingestion Failed:', err);
                document.ragStatus = 'failed';
                await document.save();
            });

        res.json({ message: 'Processing started', status: 'processing' });
    } catch (error) {
        console.error('Process Document Error:', error);
        res.status(500).json({ message: 'Internal Server Error', error: error.message });
    }
};

exports.queryRAG = async (req, res) => {
    try {
        const { query, mode, llmConfig } = req.body;
        if (!query) {
            return res.status(400).json({ message: 'Query is required' });
        }

        const stream = await ragService.query(query, mode, llmConfig);

        // Set headers for SSE
        res.setHeader('Content-Type', 'text/event-stream');
        res.setHeader('Cache-Control', 'no-cache');
        res.setHeader('Connection', 'keep-alive');

        // Pipe the stream from ragService to the client
        stream.pipe(res);

        // Handle stream errors
        stream.on('error', (err) => {
            console.error('Stream Error:', err);
            res.end();
        });
    } catch (error) {
        console.error('Query RAG Controller Error:', error); // Log full error object
        res.status(500).json({
            message: 'Internal Server Error',
            error: error.message,
            details: error.response ? error.response.data : null
        });
    }
};

