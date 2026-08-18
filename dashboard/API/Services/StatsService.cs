using API.Models.Responses;
using API.Repositories;
using MongoDB.Bson;
using MongoDB.Driver;

namespace API.Services;

public class StatsService
{
    private readonly MongoContext _mongoContext;

    public StatsService(MongoContext mongoContext)
    {
        _mongoContext = mongoContext;
    }

    public async Task<OverviewStatsDto> GetOverviewAsync()
    {
        var usersCol = _mongoContext.Database.GetCollection<BsonDocument>("Users");
        var portfoliosCol = _mongoContext.Database.GetCollection<BsonDocument>("Portfolios");
        var alertsCol = _mongoContext.Database.GetCollection<BsonDocument>("PriceAlerts");
        var groupsCol = _mongoContext.Database.GetCollection<BsonDocument>("Groups");

        var twentyFourHoursAgo = DateTime.UtcNow.AddHours(-24);
        var activeFilter = Builders<BsonDocument>.Filter.Gte("last_active", twentyFourHoursAgo);

        var totalUsers = await usersCol.CountDocumentsAsync(new BsonDocument());
        var totalPortfolios = await portfoliosCol.CountDocumentsAsync(new BsonDocument());
        var totalAlerts = await alertsCol.CountDocumentsAsync(new BsonDocument());
        var totalGroups = await groupsCol.CountDocumentsAsync(new BsonDocument());
        var activeUsers = await usersCol.CountDocumentsAsync(activeFilter);

        return new OverviewStatsDto
        {
            TotalUsers = totalUsers,
            Dau = activeUsers,
            Wau = activeUsers,
            Mau = activeUsers,
            Premium = 0,
            TotalGroups = totalGroups,
            ActiveAlerts = totalAlerts,
            RequestsToday = 0,
            RequestsWeek = 0,
            ErrorsToday = 0,
            ParserCyclesToday = 0,
            RetentionRate = 100.0
        };
    }

    public async Task<ActivityChartResponseDto> GetActivityChartAsync(int days)
    {
        // Placeholder for timeseries aggregation
        // In the real system, you would aggregate the 'Requests' or 'Users' collection over time
        var dto = new ActivityChartResponseDto();
        for (int i = days; i >= 0; i--)
        {
            dto.Days.Add(new ActivityPointDto {
                Date = DateTime.UtcNow.AddDays(-i).ToString("MMM dd"),
                Dau = new Random().Next(100, 500),
                Requests = new Random().Next(1000, 5000)
            });
        }
        return dto;
    }

    public async Task<UserStatsDto> GetUserStatsAsync()
    {
        var usersCol = _mongoContext.Database.GetCollection<BsonDocument>("Users");

        var langAggregation = await usersCol.Aggregate()
            .Group(new BsonDocument { { "_id", "$language" }, { "count", new BsonDocument("$sum", 1) } })
            .ToListAsync();

        var byLang = new List<UserLanguageStatDto>();
        foreach (var doc in langAggregation)
        {
            var lang = doc.Contains("_id") && !doc["_id"].IsBsonNull ? doc["_id"].AsString : "unknown";
            byLang.Add(new UserLanguageStatDto { Language = lang, Count = doc["count"].AsInt32 });
        }

        // Top users by requests (if tracked) - placeholder
        var topUsers = new List<TopUserDto>
        {
            new TopUserDto { Id = 1, Username = "Admin", Language = "en", Premium = true, Requests = 5000, LastActive = DateTime.UtcNow.ToString("O") }
        };

        return new UserStatsDto
        {
            ByLanguage = byLang,
            TopUsers = topUsers
        };
    }

    public async Task<DatabaseStatsDto> GetDatabaseStatsAsync()
    {
        var db = _mongoContext.Database;
        var collections = await db.ListCollectionNamesAsync();
        var collectionNames = await collections.ToListAsync();

        var stats = new DatabaseStatsDto { 
            NumCollections = collectionNames.Count,
            ConnectionsCurrent = 1,
            ConnectionsAvailable = 99
        };

        foreach (var colName in collectionNames)
        {
            var cmd = new BsonDocument("collStats", colName);
            try
            {
                var result = await db.RunCommandAsync<BsonDocument>(cmd);
                stats.Collections.Add(new CollectionStatDto
                {
                    Name = colName,
                    Count = result.GetValue("count", 0).ToInt64(),
                    SizeKb = result.GetValue("size", 0).ToDouble() / 1024.0,
                    AvgObjSizeBytes = result.GetValue("avgObjSize", 0).ToDouble()
                });
            }
            catch
            {
                // Ignore views or collections that don't support collStats
            }
        }

        stats.TotalSizeMb = stats.Collections.Sum(c => c.SizeKb) / 1024.0;
        return stats;
    }
}
