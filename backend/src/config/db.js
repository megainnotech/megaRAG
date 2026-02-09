const { Sequelize } = require('sequelize');
require('dotenv').config();

console.log('DB Config:', {
    host: process.env.DB_HOST,
    user: process.env.DB_USER,
    db: process.env.DB_NAME
});

const sequelize = new Sequelize(
    process.env.DB_NAME || 'docs_db',
    process.env.DB_USER || 'user',
    process.env.DB_PASSWORD || 'password',
    {
        host: process.env.DB_HOST || 'postgres',
        dialect: 'postgres',
        logging: false,
    }
);

const db = {};
db.Sequelize = Sequelize;
db.sequelize = sequelize;

// Import models
db.Document = require('../models/document')(sequelize, Sequelize);

module.exports = db;
