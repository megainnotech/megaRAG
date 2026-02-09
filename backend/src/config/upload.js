const multer = require('multer');
const path = require('path');
const fs = require('fs');
const { v4: uuidv4 } = require('uuid');

const UPLOAD_DIR = path.join(__dirname, '../../public/files');

if (!fs.existsSync(UPLOAD_DIR)) {
    fs.mkdirSync(UPLOAD_DIR, { recursive: true });
}

const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, UPLOAD_DIR);
    },
    filename: (req, file, cb) => {
        // Keep original extension, but use UUID to prevent collision
        const ext = path.extname(file.originalname);
        const id = uuidv4();
        cb(null, `${id}${ext}`);
    }
});

const fileFilter = (req, file, cb) => {
    const allowedMimeTypes = [
        'application/pdf',
        'text/plain',
        'application/zip',
        'application/x-zip-compressed',
        'application/x-zip'
    ];

    if (allowedMimeTypes.includes(file.mimetype) || file.originalname.endsWith('.zip')) {
        cb(null, true);
    } else {
        cb(new Error('Only PDF, Text, or Zip files are allowed'), false);
    }
};

const upload = multer({
    storage: storage,
    fileFilter: fileFilter,
    limits: { fileSize: 10 * 1024 * 1024 } // 10MB limit
});

module.exports = upload;
