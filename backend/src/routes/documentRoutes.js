const express = require('express');
const router = express.Router();
const documentController = require('../controllers/documentController');
const upload = require('../config/upload');

router.post('/git', documentController.createGitDocument);
router.post('/upload', upload.single('file'), documentController.createFileDocument);
router.get('/', documentController.getAllDocuments);
router.delete('/:id', documentController.deleteDocument);

module.exports = router;
