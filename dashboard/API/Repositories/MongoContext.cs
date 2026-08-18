using MongoDB.Driver;

namespace API.Repositories;

public class MongoContext
{
    private readonly IMongoDatabase _database;

    public MongoContext(IConfiguration configuration)
    {
        var connectionString = configuration["MONGO_URI"];
        var databaseName = configuration["MONGO_DATABASE"] ?? "finances";

        var client = new MongoClient(connectionString);
        _database = client.GetDatabase(databaseName);
    }

    public IMongoDatabase Database => _database;

    public IMongoCollection<dynamic> Users => _database.GetCollection<dynamic>("Users");
    
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
}
