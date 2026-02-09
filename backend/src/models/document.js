module.exports = (sequelize, DataTypes) => {
    const Document = sequelize.define('Document', {
        id: {
            type: DataTypes.UUID,
            defaultValue: DataTypes.UUIDV4,
            primaryKey: true,
        },
        title: {
            type: DataTypes.STRING,
            allowNull: false,
        },
        type: {
            type: DataTypes.ENUM('git', 'file'),
            allowNull: false,
        },
        sourceUrl: {
            type: DataTypes.STRING,
            allowNull: true,
        },
        localPath: {
            type: DataTypes.STRING,
            allowNull: false,
        },
        tags: {
            type: DataTypes.JSONB,
            defaultValue: {},
            allowNull: true,
        },
        branch: {
            type: DataTypes.STRING,
            allowNull: true,
        }
    });

    return Document;
};
