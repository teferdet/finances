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

    // ── Overview ──────────────────────────────────────────────────────────────

    public async Task<OverviewStatsDto> GetOverviewAsync()
    {
        var db = _mongoContext.Database;
        var usersCol     = db.GetCollection<BsonDocument>("Users");
        var alertsCol    = db.GetCollection<BsonDocument>("Alerts");
        var groupsCol    = db.GetCollection<BsonDocument>("Groups");

        var now              = DateTime.UtcNow;
        var yesterday        = now.AddHours(-24);
        var sevenDaysAgo     = now.AddDays(-7);
        var thirtyDaysAgo    = now.AddDays(-30);
        var todayMidnight    = now.Date;
        var weekMidnight     = now.AddDays(-7).Date;

        // Run all count queries in parallel
        var totalTask        = usersCol.CountDocumentsAsync(BsonDocument.Parse("{}"));
        var dauTask          = usersCol.CountDocumentsAsync(Filter("last_active", "$gte", yesterday));
        var wauTask          = usersCol.CountDocumentsAsync(Filter("last_active", "$gte", sevenDaysAgo));
        var mauTask          = usersCol.CountDocumentsAsync(Filter("last_active", "$gte", thirtyDaysAgo));
        var premiumTask      = usersCol.CountDocumentsAsync(Builders<BsonDocument>.Filter.Eq("Premium", true));
        var newTodayTask     = usersCol.CountDocumentsAsync(Filter("Sign up", "$gte", todayMidnight.ToString("o")));
        var newWeekTask      = usersCol.CountDocumentsAsync(Filter("Sign up", "$gte", weekMidnight.ToString("o")));
        var alertsTask       = alertsCol.CountDocumentsAsync(Builders<BsonDocument>.Filter.Eq("triggered", false));
        var groupsTask       = groupsCol.CountDocumentsAsync(Builders<BsonDocument>.Filter.Eq("Status", "Active"));

        await Task.WhenAll(totalTask, dauTask, wauTask, mauTask, premiumTask,
                           newTodayTask, newWeekTask, alertsTask, groupsTask);

        // Count portfolio assets (sum across all users — uses aggregation)
        long totalPortfolios = await CountTotalPortfolioAssetsAsync(usersCol);

        // Request counts come from users.stats.total_requests / requests_today
        var (reqToday, reqWeek) = await SumRequestStatsAsync(usersCol, todayMidnight, weekMidnight);

        // Retention = MAU / total * 100
        double retention = totalTask.Result > 0
            ? Math.Round((double)mauTask.Result / totalTask.Result * 100, 1)
            : 0;

        return new OverviewStatsDto
        {
            TotalUsers       = totalTask.Result,
            Dau              = dauTask.Result,
            Wau              = wauTask.Result,
            Mau              = mauTask.Result,
            Premium          = premiumTask.Result,
            NewUsersToday    = newTodayTask.Result,
            NewUsersWeek     = newWeekTask.Result,
            TotalPortfolios  = totalPortfolios,
            TotalGroups      = groupsTask.Result,
            ActiveAlerts     = alertsTask.Result,
            RequestsToday    = reqToday,
            RequestsWeek     = reqWeek,
            ErrorsToday      = 0,
            ParserCyclesToday = 0,
            RetentionRate    = retention,
        };
    }

    // ── Activity chart ────────────────────────────────────────────────────────

    /// <summary>
    /// Returns daily DAU + new user registrations for the last <paramref name="days"/> days.
    /// Aggregates real data from the Users collection (last_active + Sign up fields).
    /// </summary>
    public async Task<ActivityChartResponseDto> GetActivityChartAsync(int days)
    {
        var db       = _mongoContext.Database;
        var usersCol = db.GetCollection<BsonDocument>("Users");

        var since = DateTime.UtcNow.AddDays(-days).Date;

        // Aggregate DAU per day: group by date(last_active)
        var dauPipeline = new[]
        {
            new BsonDocument("$match", new BsonDocument("last_active",
                new BsonDocument("$gte", since))),
            new BsonDocument("$group", new BsonDocument
            {
                { "_id", new BsonDocument("$dateToString",
                    new BsonDocument { { "format", "%Y-%m-%d" }, { "date", "$last_active" } }) },
                { "dau", new BsonDocument("$sum", 1) }
            }),
        };

        // Aggregate new users per day: group by date(Sign up)
        var newUsersPipeline = new[]
        {
            new BsonDocument("$match", new BsonDocument("Sign up",
                new BsonDocument("$gte", since.ToString("o")))),
            new BsonDocument("$group", new BsonDocument
            {
                { "_id", new BsonDocument("$dateToString",
                    new BsonDocument { { "format", "%Y-%m-%d" }, { "date", new BsonDocument("$toDate", "$Sign up") } }) },
                { "new_users", new BsonDocument("$sum", 1) }
            }),
        };

        var dauResult      = await usersCol.AggregateAsync<BsonDocument>(dauPipeline);
        var dauDocs        = await dauResult.ToListAsync();
        var newUsersResult = await usersCol.AggregateAsync<BsonDocument>(newUsersPipeline);
        var newUsersDocs   = await newUsersResult.ToListAsync();

        // Build lookup dictionaries
        var dauByDate      = dauDocs.ToDictionary(
            d => d["_id"].AsString, d => d["dau"].AsInt32);
        var newByDate      = newUsersDocs.ToDictionary(
            d => d["_id"].AsString, d => d["new_users"].AsInt32);

        // Fill in every day in the range (even days with 0 activity)
        var dto = new ActivityChartResponseDto();
        for (int i = days; i >= 0; i--)
        {
            var date = DateTime.UtcNow.AddDays(-i).Date;
            var key  = date.ToString("yyyy-MM-dd");
            dto.Days.Add(new ActivityPointDto
            {
                Date     = date.ToString("MMM dd"),
                Dau      = dauByDate.GetValueOrDefault(key, 0),
                NewUsers = newByDate.GetValueOrDefault(key, 0),
            });
        }

        return dto;
    }

    // ── User stats ────────────────────────────────────────────────────────────

    /// <summary>
    /// Returns language distribution and a paginated/filtered/sorted list of users.
    /// </summary>
    public async Task<UserStatsDto> GetUserStatsAsync(
        int page = 1,
        int limit = 50,
        string? search = null,
        string? language = null,
        bool? premium = null,
        string sort = "last_active",
        string order = "desc")
    {
        var db       = _mongoContext.Database;
        var usersCol = db.GetCollection<BsonDocument>("Users");
        var alertsCol= db.GetCollection<BsonDocument>("Alerts");

        // ── Language aggregation ─────────────────────────────────────────────
        var langAgg = await usersCol.Aggregate()
            .Group(new BsonDocument
            {
                { "_id", "$Language" },
                { "count", new BsonDocument("$sum", 1) }
            })
            .ToListAsync();

        var byLang = langAgg.Select(d => new UserLanguageStatDto
        {
            Language = d.Contains("_id") && !d["_id"].IsBsonNull ? d["_id"].AsString : "unknown",
            Count    = d["count"].AsInt32,
        }).OrderByDescending(x => x.Count).ToList();

        // ── Build filter ─────────────────────────────────────────────────────
        var filters = new List<FilterDefinition<BsonDocument>>();

        if (!string.IsNullOrWhiteSpace(search))
        {
            // Search by username (case-insensitive) or by numeric ID
            if (long.TryParse(search, out var searchId))
            {
                filters.Add(Builders<BsonDocument>.Filter.Eq("_id", searchId));
            }
            else
            {
                var regex = new BsonRegularExpression(search, "i");
                filters.Add(Builders<BsonDocument>.Filter.Or(
                    Builders<BsonDocument>.Filter.Regex("Username", regex),
                    Builders<BsonDocument>.Filter.Regex("Name", regex)
                ));
            }
        }

        if (!string.IsNullOrWhiteSpace(language))
            filters.Add(Builders<BsonDocument>.Filter.Eq("Language", language));

        if (premium.HasValue)
            filters.Add(Builders<BsonDocument>.Filter.Eq("Premium", premium.Value));

        var filter = filters.Count > 0
            ? Builders<BsonDocument>.Filter.And(filters)
            : Builders<BsonDocument>.Filter.Empty;

        // ── Sort ─────────────────────────────────────────────────────────────
        var sortField = sort switch
        {
            "requests" => "stats.total_requests",
            "premium"  => "Premium",
            "language" => "Language",
            _          => "last_active",
        };
        var sortDef = order == "asc"
            ? Builders<BsonDocument>.Sort.Ascending(sortField)
            : Builders<BsonDocument>.Sort.Descending(sortField);

        // ── Pagination ───────────────────────────────────────────────────────
        limit = Math.Clamp(limit, 1, 200);
        page  = Math.Max(1, page);
        var skip = (page - 1) * limit;

        var total   = await usersCol.CountDocumentsAsync(filter);
        var userDocs = await usersCol.Find(filter)
            .Sort(sortDef)
            .Skip(skip)
            .Limit(limit)
            .ToListAsync();

        // ── Enrich each user ─────────────────────────────────────────────────
        var now = DateTime.UtcNow;
        var activeThreshold = now.AddHours(-24);

        var items = new List<TopUserDto>();
        foreach (var u in userDocs)
        {
            var uid = u["_id"].IsInt64 ? u["_id"].AsInt64 : u["_id"].AsInt32;

            // Count alerts for this user
            var alertCount = (int)await alertsCol.CountDocumentsAsync(
                Builders<BsonDocument>.Filter.Eq("user_id", uid));

            // Count portfolio assets
            int portfolioAssets = 0;
            if (u.Contains("portfolio") && u["portfolio"].IsBsonDocument)
            {
                var p = u["portfolio"].AsBsonDocument;
                foreach (var section in new[] { "crypto", "stock", "fiat" })
                    if (p.Contains(section) && p[section].IsBsonArray)
                        portfolioAssets += p[section].AsBsonArray.Count;
            }

            // Determine if user is active (last 24h)
            bool isActive = false;
            if (u.Contains("last_active") && !u["last_active"].IsBsonNull)
            {
                if (u["last_active"].BsonType == BsonType.DateTime)
                    isActive = u["last_active"].ToUniversalTime() >= activeThreshold;
            }

            items.Add(new TopUserDto
            {
                Id             = uid,
                Username       = GetStr(u, "Username"),
                Name           = GetStr(u, "Name"),
                Language       = GetStr(u, "Language") ?? "unknown",
                Premium        = GetBool(u, "Premium"),
                TotalRequests  = GetInt(u.Contains("stats") && u["stats"].IsBsonDocument
                                     ? u["stats"].AsBsonDocument : new BsonDocument(),
                                     "total_requests"),
                LastActive     = GetDateStr(u, "last_active"),
                FirstSeen      = GetStr(u, "Sign up"),
                IsActive       = isActive,
                AlertsCount    = alertCount,
                PortfolioAssets = portfolioAssets,
            });
        }

        return new UserStatsDto
        {
            ByLanguage = byLang,
            TopUsers   = new PagedResult<TopUserDto>
            {
                Items = items,
                Total = total,
                Page  = page,
                Limit = limit,
            },
        };
    }

    // ── Database stats ────────────────────────────────────────────────────────

    public async Task<DatabaseStatsDto> GetDatabaseStatsAsync()
    {
        var db = _mongoContext.Database;

        // dbStats for top-level size info
        BsonDocument dbStats;
        try
        {
            dbStats = await db.RunCommandAsync<BsonDocument>(new BsonDocument("dbStats", 1));
        }
        catch
        {
            dbStats = new BsonDocument();
        }

        // serverStatus for connections + version
        BsonDocument serverStatus;
        try
        {
            serverStatus = await db.RunCommandAsync<BsonDocument>(
                new BsonDocument("serverStatus", 1));
        }
        catch
        {
            serverStatus = new BsonDocument();
        }

        var stats = new DatabaseStatsDto
        {
            TotalSizeMb        = GetDouble(dbStats, "dataSize")    / 1024 / 1024,
            StorageSizeMb      = GetDouble(dbStats, "storageSize") / 1024 / 1024,
            IndexSizeMb        = GetDouble(dbStats, "indexSize")   / 1024 / 1024,
            MongoVersion       = GetNestedStr(serverStatus, "version") ?? "unknown",
            ConnectionsCurrent = GetNestedInt(serverStatus, "connections", "current"),
            ConnectionsAvailable = GetNestedInt(serverStatus, "connections", "available"),
        };

        // Per-collection stats
        var collectionNames = await (await db.ListCollectionNamesAsync()).ToListAsync();
        foreach (var name in collectionNames)
        {
            try
            {
                var colStats = await db.RunCommandAsync<BsonDocument>(
                    new BsonDocument("collStats", name));
                stats.Collections.Add(new CollectionStatDto
                {
                    Name           = name,
                    Count          = colStats.GetValue("count", 0).ToInt64(),
                    SizeKb         = colStats.GetValue("size", 0).ToDouble() / 1024.0,
                    AvgObjSizeBytes = colStats.GetValue("avgObjSize", 0).ToDouble(),
                });
            }
            catch { /* skip views or collections that don't support collStats */ }
        }

        stats.NumCollections = stats.Collections.Count;
        return stats;
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static FilterDefinition<BsonDocument> Filter(string field, string op, object value)
        => new BsonDocument(field, new BsonDocument(op, BsonValue.Create(value)));

    private static string? GetStr(BsonDocument doc, string key)
        => doc.Contains(key) && !doc[key].IsBsonNull ? doc[key].ToString() : null;

    private static bool GetBool(BsonDocument doc, string key, bool def = false)
        => doc.Contains(key) && doc[key].IsBoolean ? doc[key].AsBoolean : def;

    private static int GetInt(BsonDocument doc, string key, int def = 0)
        => doc.Contains(key) && !doc[key].IsBsonNull && doc[key].IsInt32 ? doc[key].AsInt32 : def;

    private static double GetDouble(BsonDocument doc, string key, double def = 0)
    {
        if (!doc.Contains(key) || doc[key].IsBsonNull) return def;
        var v = doc[key];
        return v.IsDouble ? v.AsDouble : v.IsInt32 ? v.AsInt32 : v.IsInt64 ? v.AsInt64 : def;
    }

    private static string? GetDateStr(BsonDocument doc, string key)
    {
        if (!doc.Contains(key) || doc[key].IsBsonNull) return null;
        return doc[key].BsonType == BsonType.DateTime
            ? doc[key].ToUniversalTime().ToString("O")
            : doc[key].ToString();
    }

    private static string? GetNestedStr(BsonDocument doc, string key)
        => doc.Contains(key) && !doc[key].IsBsonNull ? doc[key].ToString() : null;

    private static int GetNestedInt(BsonDocument doc, string section, string key)
    {
        if (!doc.Contains(section) || !doc[section].IsBsonDocument) return 0;
        var sub = doc[section].AsBsonDocument;
        return GetInt(sub, key);
    }

    private async Task<long> CountTotalPortfolioAssetsAsync(IMongoCollection<BsonDocument> usersCol)
    {
        try
        {
            var pipeline = new[]
            {
                new BsonDocument("$project", new BsonDocument
                {
                    { "assetCount", new BsonDocument("$add", new BsonArray
                        {
                            new BsonDocument("$size", new BsonDocument("$ifNull",
                                new BsonArray { new BsonDocument("$ifNull",
                                    new BsonArray { "$portfolio.crypto", new BsonArray() }), new BsonArray() })),
                            new BsonDocument("$size", new BsonDocument("$ifNull",
                                new BsonArray { new BsonDocument("$ifNull",
                                    new BsonArray { "$portfolio.stock", new BsonArray() }), new BsonArray() })),
                            new BsonDocument("$size", new BsonDocument("$ifNull",
                                new BsonArray { new BsonDocument("$ifNull",
                                    new BsonArray { "$portfolio.fiat", new BsonArray() }), new BsonArray() })),
                        })
                    }
                }),
                new BsonDocument("$group", new BsonDocument
                {
                    { "_id", BsonNull.Value },
                    { "total", new BsonDocument("$sum", "$assetCount") }
                })
            };

            var result = await usersCol.AggregateAsync<BsonDocument>(pipeline);
            var doc = await result.FirstOrDefaultAsync();
            return doc != null ? doc["total"].ToInt64() : 0;
        }
        catch { return 0; }
    }

    private async Task<(long Today, long Week)> SumRequestStatsAsync(
        IMongoCollection<BsonDocument> usersCol,
        DateTime todayMidnight,
        DateTime weekMidnight)
    {
        try
        {
            var pipeline = new[]
            {
                new BsonDocument("$group", new BsonDocument
                {
                    { "_id", BsonNull.Value },
                    { "today", new BsonDocument("$sum", "$stats.requests_today") },
                    { "week",  new BsonDocument("$sum", "$stats.total_requests") }
                })
            };
            var result = await usersCol.AggregateAsync<BsonDocument>(pipeline);
            var doc = await result.FirstOrDefaultAsync();
            if (doc == null) return (0, 0);
            return (doc["today"].ToInt64(), doc["week"].ToInt64());
        }
        catch { return (0, 0); }
    }
}
