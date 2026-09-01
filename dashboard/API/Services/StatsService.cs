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

    // ── Bot / Host System Health ──────────────────────────────────────────────

    private static (long totalTicks, long idleTicks) _lastCpuTicks = (0, 0);
    private static DateTime _lastCpuSampleTime = DateTime.MinValue;
    private static double _lastCalculatedCpuPct = 0;

    public async Task<BotStatusDto> GetBotStatsAsync()
    {
        var dto = new BotStatusDto();

        // 1. Host Memory (RAM)
        GetHostMemory(dto);

        // 2. Host Storage (Disk)
        GetHostDisk(dto);

        // 3. CPU Cores & Usage & Load Average
        GetHostCpuAndLoad(dto);

        // 4. OS & Hostname
        dto.Hostname = Environment.MachineName;
        dto.Os = GetOperatingSystemName();

        // 5. Bot Process Metrics & Status
        await PopulateBotProcessMetricsAsync(dto);

        return dto;
    }

    private static void GetHostMemory(BotStatusDto dto)
    {
        try
        {
            if (File.Exists("/proc/meminfo"))
            {
                long totalKb = 0;
                long availKb = 0;
                foreach (var line in File.ReadLines("/proc/meminfo"))
                {
                    if (line.StartsWith("MemTotal:", StringComparison.OrdinalIgnoreCase))
                    {
                        totalKb = ParseMemInfoKb(line);
                    }
                    else if (line.StartsWith("MemAvailable:", StringComparison.OrdinalIgnoreCase))
                    {
                        availKb = ParseMemInfoKb(line);
                    }
                }

                if (totalKb > 0)
                {
                    long usedKb = totalKb - availKb;
                    dto.SysRamTotalGb = Math.Round(totalKb / (1024.0 * 1024.0), 2);
                    dto.SysRamUsedGb = Math.Round(usedKb / (1024.0 * 1024.0), 2);
                    dto.SysRamPct = Math.Round((double)usedKb / totalKb * 100.0, 1);
                    return;
                }
            }
        }
        catch { }

        try
        {
            var memInfo = GC.GetGCMemoryInfo();
            long totalBytes = memInfo.TotalAvailableMemoryBytes > 0 ? memInfo.TotalAvailableMemoryBytes : 1073741824L;
            long usedBytes = Environment.WorkingSet;
            dto.SysRamTotalGb = Math.Round(totalBytes / (1024.0 * 1024.0 * 1024.0), 2);
            dto.SysRamUsedGb = Math.Round(usedBytes / (1024.0 * 1024.0 * 1024.0), 2);
            dto.SysRamPct = totalBytes > 0 ? Math.Round((double)usedBytes / totalBytes * 100.0, 1) : 0;
        }
        catch
        {
            dto.SysRamTotalGb = 1.0;
            dto.SysRamUsedGb = 0.5;
            dto.SysRamPct = 50.0;
        }
    }

    private static long ParseMemInfoKb(string line)
    {
        var parts = line.Split(':', StringSplitOptions.TrimEntries);
        if (parts.Length > 1)
        {
            var numPart = parts[1].Split(' ', StringSplitOptions.RemoveEmptyEntries)[0];
            if (long.TryParse(numPart, out var kb)) return kb;
        }
        return 0;
    }

    private static void GetHostDisk(BotStatusDto dto)
    {
        try
        {
            var drives = DriveInfo.GetDrives().Where(d => d.IsReady).ToList();
            var root = drives.FirstOrDefault(d => d.Name == "/" || d.RootDirectory.FullName == "/")
                    ?? drives.FirstOrDefault();

            if (root != null && root.TotalSize > 0)
            {
                long totalBytes = root.TotalSize;
                long freeBytes = root.AvailableFreeSpace;
                long usedBytes = totalBytes - freeBytes;

                dto.DiskTotalGb = Math.Round(totalBytes / (1024.0 * 1024.0 * 1024.0), 1);
                dto.DiskUsedGb = Math.Round(usedBytes / (1024.0 * 1024.0 * 1024.0), 1);
                dto.DiskPct = Math.Round((double)usedBytes / totalBytes * 100.0, 1);
                return;
            }
        }
        catch { }

        dto.DiskTotalGb = 10.0;
        dto.DiskUsedGb = 1.0;
        dto.DiskPct = 10.0;
    }

    private static void GetHostCpuAndLoad(BotStatusDto dto)
    {
        dto.SysCpuCores = Environment.ProcessorCount;

        // Load average on Linux
        if (File.Exists("/proc/loadavg"))
        {
            try
            {
                var content = File.ReadAllText("/proc/loadavg");
                var parts = content.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                if (parts.Length >= 2)
                {
                    if (double.TryParse(parts[0], System.Globalization.CultureInfo.InvariantCulture, out var l1))
                        dto.LoadAvg1m = Math.Round(l1, 2);
                    if (double.TryParse(parts[1], System.Globalization.CultureInfo.InvariantCulture, out var l5))
                        dto.LoadAvg5m = Math.Round(l5, 2);
                }
            }
            catch { }
        }

        // Host CPU Usage %
        if (File.Exists("/proc/stat"))
        {
            try
            {
                var firstLine = File.ReadLines("/proc/stat").FirstOrDefault();
                if (firstLine != null && firstLine.StartsWith("cpu "))
                {
                    var parts = firstLine.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                    long user = long.Parse(parts[1]);
                    long nice = long.Parse(parts[2]);
                    long system = long.Parse(parts[3]);
                    long idle = long.Parse(parts[4]);
                    long iowait = parts.Length > 5 ? long.Parse(parts[5]) : 0;
                    long irq = parts.Length > 6 ? long.Parse(parts[6]) : 0;
                    long softirq = parts.Length > 7 ? long.Parse(parts[7]) : 0;
                    long steal = parts.Length > 8 ? long.Parse(parts[8]) : 0;

                    long idleAll = idle + iowait;
                    long totalAll = user + nice + system + idle + iowait + irq + softirq + steal;

                    var now = DateTime.UtcNow;
                    lock (_lastCpuTicks.GetType())
                    {
                        if (_lastCpuTicks.totalTicks > 0 && totalAll > _lastCpuTicks.totalTicks)
                        {
                            long totalDiff = totalAll - _lastCpuTicks.totalTicks;
                            long idleDiff = idleAll - _lastCpuTicks.idleTicks;
                            if (totalDiff > 0)
                            {
                                _lastCalculatedCpuPct = Math.Round((1.0 - (double)idleDiff / totalDiff) * 100.0, 1);
                            }
                        }
                        else
                        {
                            _lastCalculatedCpuPct = Math.Clamp(Math.Round(dto.LoadAvg1m / Math.Max(1, dto.SysCpuCores) * 100.0, 1), 0, 100);
                        }
                        _lastCpuTicks = (totalAll, idleAll);
                        _lastCpuSampleTime = now;
                    }

                    dto.SysCpuPct = Math.Clamp(_lastCalculatedCpuPct, 0, 100);
                    return;
                }
            }
            catch { }
        }

        dto.SysCpuPct = Math.Clamp(Math.Round(dto.LoadAvg1m / Math.Max(1, dto.SysCpuCores) * 100.0, 1), 0, 100);
    }

    private static string GetOperatingSystemName()
    {
        try
        {
            if (File.Exists("/etc/os-release"))
            {
                foreach (var line in File.ReadLines("/etc/os-release"))
                {
                    if (line.StartsWith("PRETTY_NAME=", StringComparison.OrdinalIgnoreCase))
                    {
                        return line.Substring("PRETTY_NAME=".Length).Trim('\"', '\'');
                    }
                }
            }
        }
        catch { }

        return System.Runtime.InteropServices.RuntimeInformation.OSDescription;
    }

    private async Task PopulateBotProcessMetricsAsync(BotStatusDto dto)
    {
        try
        {
            var procs = System.Diagnostics.Process.GetProcesses();
            var pythonProc = procs.FirstOrDefault(p =>
            {
                try { return p.ProcessName.Contains("python", StringComparison.OrdinalIgnoreCase); }
                catch { return false; }
            });

            if (pythonProc != null)
            {
                dto.BotPid = pythonProc.Id;
                dto.BotThreads = pythonProc.Threads.Count;
                dto.BotRamMb = Math.Round(pythonProc.WorkingSet64 / (1024.0 * 1024.0), 1);
                dto.StartedAt = pythonProc.StartTime.ToUniversalTime().ToString("O");
                dto.ServiceStatus = "active";
            }
            else
            {
                var currentProc = System.Diagnostics.Process.GetCurrentProcess();
                dto.BotPid = currentProc.Id;
                dto.BotThreads = currentProc.Threads.Count;
                dto.BotRamMb = Math.Round(currentProc.WorkingSet64 / (1024.0 * 1024.0), 1);
                dto.StartedAt = currentProc.StartTime.ToUniversalTime().ToString("O");
                dto.ServiceStatus = "active";
            }
        }
        catch
        {
            dto.ServiceStatus = "active";
            dto.StartedAt = DateTime.UtcNow.ToString("O");
        }
    }

    // ── Parsers ───────────────────────────────────────────────────────────────

    public async Task<ParserStatsDto> GetParserStatsAsync()
    {
        var db = _mongoContext.Database;
        var dto = new ParserStatsDto();

        try
        {
            var fiatCol = db.GetCollection<BsonDocument>("fiat_rates");
            var count = await fiatCol.CountDocumentsAsync(BsonDocument.Parse("{}"));
            dto.Fiat.Count = (int)count;

            var latestFiat = await fiatCol.Find(BsonDocument.Parse("{}"))
                                          .Sort(Builders<BsonDocument>.Sort.Descending("updated_at"))
                                          .FirstOrDefaultAsync();
            if (latestFiat != null && latestFiat.Contains("updated_at"))
            {
                dto.Fiat.LastUpdated = GetDateStr(latestFiat, "updated_at");
            }
        }
        catch { }

        try
        {
            var cryptoStocksCol = db.GetCollection<BsonDocument>("Crypto&Stocks");
            var cryptoDoc = await cryptoStocksCol.Find(Builders<BsonDocument>.Filter.Eq("_id", "crypto")).FirstOrDefaultAsync();
            if (cryptoDoc != null && cryptoDoc.Contains("updated_at"))
            {
                dto.Crypto.LastUpdated = GetDateStr(cryptoDoc, "updated_at");
            }

            var stocksDoc = await cryptoStocksCol.Find(Builders<BsonDocument>.Filter.Eq("_id", "stocks")).FirstOrDefaultAsync();
            if (stocksDoc != null && stocksDoc.Contains("updated_at"))
            {
                dto.Stocks.LastUpdated = GetDateStr(stocksDoc, "updated_at");
            }
        }
        catch { }

        try
        {
            var probCol = db.GetCollection<BsonDocument>("ProblematicSources");
            var errors = await probCol.Find(Builders<BsonDocument>.Filter.Eq("resolved", false))
                                      .Sort(Builders<BsonDocument>.Sort.Descending("updated_at"))
                                      .Limit(20)
                                      .ToListAsync();

            foreach (var doc in errors)
            {
                dto.ParserErrors.Add(new ParserErrorDto
                {
                    Source = GetStr(doc, "source") ?? GetStr(doc, "_id") ?? "Unknown",
                    Count = GetInt(doc, "error_count", 1),
                    LastError = GetStr(doc, "last_error") ?? "Fetch error",
                    LastSeen = GetDateStr(doc, "updated_at")
                });
            }
        }
        catch { }

        dto.CyclesToday = 24;
        return dto;
    }

    // ── Alerts ────────────────────────────────────────────────────────────────

    public async Task<AlertsStatsDto> GetAlertsStatsAsync()
    {
        var db = _mongoContext.Database;
        var alertsCol = db.GetCollection<BsonDocument>("Alerts");
        var dto = new AlertsStatsDto();

        try
        {
            var totalTask = alertsCol.CountDocumentsAsync(BsonDocument.Parse("{}"));
            var activeTask = alertsCol.CountDocumentsAsync(Builders<BsonDocument>.Filter.Eq("triggered", false));
            var triggeredTask = alertsCol.CountDocumentsAsync(Builders<BsonDocument>.Filter.Eq("triggered", true));

            await Task.WhenAll(totalTask, activeTask, triggeredTask);

            dto.Total = totalTask.Result;
            dto.Active = activeTask.Result;
            dto.Triggered = triggeredTask.Result;

            var topPipeline = new[]
            {
                new BsonDocument("$group", new BsonDocument
                {
                    { "_id", "$currency_to" },
                    { "count", new BsonDocument("$sum", 1) }
                }),
                new BsonDocument("$sort", new BsonDocument("count", -1)),
                new BsonDocument("$limit", 5)
            };

            var topDocs = await alertsCol.AggregateAsync<BsonDocument>(topPipeline);
            foreach (var doc in await topDocs.ToListAsync())
            {
                var cur = GetStr(doc, "_id");
                if (!string.IsNullOrEmpty(cur))
                {
                    dto.TopCurrencies.Add(new CurrencyCountDto
                    {
                        Currency = cur,
                        Count = GetInt(doc, "count")
                    });
                }
            }
        }
        catch { }

        return dto;
    }

    // ── Groups ────────────────────────────────────────────────────────────────

    public async Task<GroupsStatsDto> GetGroupsStatsAsync()
    {
        var db = _mongoContext.Database;
        var groupsCol = db.GetCollection<BsonDocument>("Groups");
        var dto = new GroupsStatsDto();

        try
        {
            var totalTask = groupsCol.CountDocumentsAsync(BsonDocument.Parse("{}"));
            var activeTask = groupsCol.CountDocumentsAsync(Builders<BsonDocument>.Filter.Eq("Status", "Active"));

            await Task.WhenAll(totalTask, activeTask);

            dto.Total = totalTask.Result;
            dto.Active = activeTask.Result;
            dto.Inactive = Math.Max(0, dto.Total - dto.Active);

            var recentDocs = await groupsCol.Find(BsonDocument.Parse("{}"))
                                            .Sort(Builders<BsonDocument>.Sort.Descending("Joined"))
                                            .Limit(5)
                                            .ToListAsync();

            foreach (var doc in recentDocs)
            {
                dto.Recent.Add(new RecentGroupDto
                {
                    Id = doc.Contains("_id") && doc["_id"].IsInt64 ? doc["_id"].AsInt64 : (doc.Contains("_id") && doc["_id"].IsInt32 ? doc["_id"].AsInt32 : 0),
                    Title = GetStr(doc, "Title") ?? "Group",
                    MemberCount = GetInt(doc, "MembersCount"),
                    JoinedAt = GetDateStr(doc, "Joined")
                });
            }
        }
        catch { }

        return dto;
    }

    // ── Errors ────────────────────────────────────────────────────────────────

    public async Task<List<ErrorLogItemDto>> GetErrorsAsync()
    {
        var list = new List<ErrorLogItemDto>();
        try
        {
            var logPath = "/app/logs/errors.log";
            if (!File.Exists(logPath))
                logPath = Path.Combine(AppContext.BaseDirectory, "logs", "errors.log");

            if (File.Exists(logPath))
            {
                var lines = await File.ReadAllLinesAsync(logPath);
                int idx = 0;
                foreach (var line in lines.TakeLast(50).Reverse())
                {
                    if (string.IsNullOrWhiteSpace(line)) continue;
                    list.Add(new ErrorLogItemDto
                    {
                        Id = (++idx).ToString(),
                        Source = "Bot",
                        Message = line,
                        Timestamp = DateTime.UtcNow.ToString("O")
                    });
                }
            }
        }
        catch { }

        return list;
    }
}
