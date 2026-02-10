const axios = require('axios');

const RAG_SERVICE_URL = process.env.RAG_SERVICE_URL || 'http://rag_service:8000';

exports.ingestDocument = async (docId, type, localPath, tags) => {
    try {
        const response = await axios.post(`${RAG_SERVICE_URL}/ingest`, {
            doc_id: docId,
            type: type, // 'git', 'file', 'text'
            local_path: localPath,
            tags: tags
        });
        return response.data;
    } catch (error) {
        console.error('RAG Ingest Error:', error.message);
        throw error;
    }
};

exports.deleteDocument = async (docId) => {
    try {
        const response = await axios.delete(`${RAG_SERVICE_URL}/documents/${docId}`);
        return response.data;
    } catch (error) {
        console.error('RAG Delete Error:', error.message);
        // Don't throw, just log. We don't want to block main deletion if RAG is down.
        return null;
    }
};

exports.query = async (query, mode = 'hybrid') => {
    try {
        const response = await axios.post(`${RAG_SERVICE_URL}/query`, {
            query: query,
            mode: mode
        });
        return response.data;
    } catch (error) {
        console.error('RAG Query Error:', error.message);
        throw error;
    }
};
