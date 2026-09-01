namespace API.Models.Responses;

// ── Generic paged wrapper ─────────────────────────────────────────────────────

/// <summary>Generic pagination wrapper returned by list endpoints.</summary>
public class PagedResult<T>
{
    public List<T> Items { get; set; } = new();
    public long Total { get; set; }
    public int Page { get; set; }
    public int Limit { get; set; }
    public int Pages => Limit > 0 ? (int)Math.Ceiling((double)Total / Limit) : 0;
}

// ── Overview ──────────────────────────────────────────────────────────────────

public class OverviewStatsDto
{
    public long TotalUsers { get; set; }
    public long Dau { get; set; }
    public long Wau { get; set; }
    public long Mau { get; set; }
    public long Premium { get; set; }
    public long NewUsersToday { get; set; }
    public long NewUsersWeek { get; set; }
    public long TotalPortfolios { get; set; }
    public long TotalGroups { get; set; }
    public long ActiveAlerts { get; set; }
    public long RequestsToday { get; set; }
    public long RequestsWeek { get; set; }
    public long ErrorsToday { get; set; }
    public long ParserCyclesToday { get; set; }
    public double RetentionRate { get; set; }
}

// ── Activity chart ────────────────────────────────────────────────────────────

public class ActivityPointDto
{
    public string Date { get; set; } = string.Empty;
    public int Dau { get; set; }
    public int NewUsers { get; set; }
}

public class ActivityChartResponseDto
{
    public List<ActivityPointDto> Days { get; set; } = new();
}

// ── Users ─────────────────────────────────────────────────────────────────────

public class UserStatsDto
{
    public List<UserLanguageStatDto> ByLanguage { get; set; } = new();
    public PagedResult<TopUserDto> TopUsers { get; set; } = new();
}

public class UserLanguageStatDto
{
    public string Language { get; set; } = string.Empty;
    public int Count { get; set; }
}

public class TopUserDto
{
    public long Id { get; set; }
    public string? Username { get; set; }
    public string? Name { get; set; }
    public string Language { get; set; } = string.Empty;
    public bool Premium { get; set; }
    public int TotalRequests { get; set; }
    public string? LastActive { get; set; }
    public string? FirstSeen { get; set; }
    public bool IsActive { get; set; }
    public int AlertsCount { get; set; }
    public int PortfolioAssets { get; set; }
}

// ── Database ──────────────────────────────────────────────────────────────────

public class DatabaseStatsDto
{
    public double TotalSizeMb { get; set; }
    public double StorageSizeMb { get; set; }
    public double IndexSizeMb { get; set; }
    public List<CollectionStatDto> Collections { get; set; } = new();
    public int NumCollections { get; set; }
    public int ConnectionsCurrent { get; set; }
    public int ConnectionsAvailable { get; set; }
    public string MongoVersion { get; set; } = string.Empty;
}

public class CollectionStatDto
{
    public string Name { get; set; } = string.Empty;
    public long Count { get; set; }
    public double SizeKb { get; set; }
    public double AvgObjSizeBytes { get; set; }
}
