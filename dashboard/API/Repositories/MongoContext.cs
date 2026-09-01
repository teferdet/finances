using MongoDB.Driver;

namespace API.Repositories;

public class MongoContext
{
    private readonly IMongoDatabase _database;

    public MongoContext(IConfiguration configuration)
    {
        var connectionString = configuration["MONGO_URI"]
            ?? throw new InvalidOperationException("MONGO_URI is not configured.");
        var databaseName = configuration["MONGO_DATABASE"] ?? "finances";

        var settings = MongoClientSettings.FromConnectionString(connectionString);

        // Connection pool tuning
        settings.MinConnectionPoolSize = 2;
        settings.MaxConnectionPoolSize = 20;

        // Fail fast if MongoDB is unreachable at startup
        settings.ServerSelectionTimeout = TimeSpan.FromSeconds(10);
        settings.ConnectTimeout         = TimeSpan.FromSeconds(10);
        settings.SocketTimeout          = TimeSpan.FromSeconds(30);

        var client = new MongoClient(settings);
        _database = client.GetDatabase(databaseName);
    }

    public IMongoDatabase Database => _database;

    public IMongoCollection<dynamic> Users => _database.GetCollection<dynamic>("Users");

    /// <summary>Verify connectivity. Used by the health endpoint.</summary>
    public async Task<bool> PingAsync()
    {
        try
        {
            await _database.RunCommandAsync((Command<dynamic>)"{ping: 1}");
            return true;
        }
        catch
        {
            return false;
        }
    }

    /// <summary>
    /// Ensure indexes exist for frequently-queried fields.
    /// Safe to call on every startup (MongoDB ignores duplicates).
    /// </summary>
    public async Task EnsureIndexesAsync()
    {
        var users = _database.GetCollection<MongoDB.Bson.BsonDocument>("Users");
        var alerts = _database.GetCollection<MongoDB.Bson.BsonDocument>("Alerts");
        var otps   = _database.GetCollection<MongoDB.Bson.BsonDocument>("Otps");

        // Users
        await users.Indexes.CreateOneAsync(
            new CreateIndexModel<MongoDB.Bson.BsonDocument>(
                MongoDB.Driver.Builders<MongoDB.Bson.BsonDocument>.IndexKeys.Ascending("last_active"),
                new CreateIndexOptions { Background = true }));
        await users.Indexes.CreateOneAsync(
            new CreateIndexModel<MongoDB.Bson.BsonDocument>(
                MongoDB.Driver.Builders<MongoDB.Bson.BsonDocument>.IndexKeys.Ascending("Language"),
                new CreateIndexOptions { Background = true }));
        await users.Indexes.CreateOneAsync(
            new CreateIndexModel<MongoDB.Bson.BsonDocument>(
                MongoDB.Driver.Builders<MongoDB.Bson.BsonDocument>.IndexKeys.Ascending("Premium"),
                new CreateIndexOptions { Background = true }));

        // Alerts — already created by bot, but idempotent
        await alerts.Indexes.CreateOneAsync(
            new CreateIndexModel<MongoDB.Bson.BsonDocument>(
                MongoDB.Driver.Builders<MongoDB.Bson.BsonDocument>.IndexKeys.Ascending("user_id"),
                new CreateIndexOptions { Background = true }));

        // OTPs — TTL index: auto-delete after 10 minutes
        await otps.Indexes.CreateOneAsync(
            new CreateIndexModel<MongoDB.Bson.BsonDocument>(
                MongoDB.Driver.Builders<MongoDB.Bson.BsonDocument>.IndexKeys.Ascending("createdAt"),
                new CreateIndexOptions { ExpireAfter = TimeSpan.FromMinutes(10), Background = true }));
    }
}
