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

exports.query = async (query, mode = 'hybrid', llmConfig = {}) => {
    try {
        const response = await axios.post(`${RAG_SERVICE_URL}/query`, {
            query: query,
            mode: mode,
            llm_config: llmConfig
        }, {
            responseType: 'stream'
        });
        return response.data; // This is now a stream
    } catch (error) {
        // Enhanced logging for Grafana/Loki
        if (error.response) {
            // The request was made and the server responded with a status code
            // that falls out of the range of 2xx
            console.error('RAG Query Error Response:', {
                status: error.response.status,
                data: error.response.data,
                headers: error.response.headers
            });
        } else if (error.request) {
            // The request was made but no response was received
            console.error('RAG Query No Response:', error.request);
        } else {
            // Something happened in setting up the request that triggered an Error
            console.error('RAG Query Setup Error:', error.message);
        }
        throw error;
    }
};
