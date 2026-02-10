const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const path = require('path');
const db = require('./config/db');
const documentRoutes = require('./routes/documentRoutes');

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors({
    origin: '*', // Allow all for now to rule out simple block, or specific: ['http://localhost:5173', 'http://localhost:3000']
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization']
}));
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// Prometheus Metrics
const promMiddleware = require('express-prometheus-middleware');
app.use(promMiddleware({
    metricsPath: '/metrics',
    collectDefaultMetrics: true,
    requestDurationBuckets: [0.1, 0.5, 1, 1.5],
    requestLengthBuckets: [512, 1024, 5120, 10240, 51200, 102400],
    responseLengthBuckets: [512, 1024, 5120, 10240, 51200, 102400],
}));

// Serve static files (built MkDocs)
app.use('/docs', express.static(path.join(__dirname, '../public/docs')));

// API Routes
app.use('/api/documents', documentRoutes);

// Database sync and server start
db.sequelize.sync({ alter: true }).then(() => {
    console.log('Database synced');
    app.listen(PORT, () => {
        console.log(`Server is running on port ${PORT}`);
    });
}).catch(err => {
    console.error('Failed to sync database:', err);
});
