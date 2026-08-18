namespace API.Models.Responses;

public class OverviewStatsDto
{
    public long TotalUsers { get; set; }
    public long Dau { get; set; }
    public long Wau { get; set; }
    public long Mau { get; set; }
    public long Premium { get; set; }
    public long TotalGroups { get; set; }
    public long ActiveAlerts { get; set; }
    public long RequestsToday { get; set; }
    public long RequestsWeek { get; set; }
    public long ErrorsToday { get; set; }
    public long ParserCyclesToday { get; set; }
    public double RetentionRate { get; set; }
}

public class ActivityPointDto
{
    public string Date { get; set; } = string.Empty;
    public int Dau { get; set; }
    public int Requests { get; set; }
}

public class ActivityChartResponseDto
{
    public List<ActivityPointDto> Days { get; set; } = new();
}

public class UserStatsDto
{
    public List<UserLanguageStatDto> ByLanguage { get; set; } = new();
    public List<TopUserDto> TopUsers { get; set; } = new();
}

public class UserLanguageStatDto
{
    public string Language { get; set; } = string.Empty;
    public int Count { get; set; }
}

public class TopUserDto
{
    public long Id { get; set; }
    public string Username { get; set; } = string.Empty;
    public string Language { get; set; } = string.Empty;
    public bool Premium { get; set; }
    public int Requests { get; set; }
    public string? LastActive { get; set; }
}

public class DatabaseStatsDto
{
    public double TotalSizeMb { get; set; }
    public double StorageSizeMb { get; set; }
    public double IndexSizeMb { get; set; }
    public List<CollectionStatDto> Collections { get; set; } = new();
    public int NumCollections { get; set; }
    public int ConnectionsCurrent { get; set; }
    public int ConnectionsAvailable { get; set; }
    public string MongoVersion { get; set; } = "7.0.0";
}

public class CollectionStatDto
{
    public string Name { get; set; } = string.Empty;
    public long Count { get; set; }
    public double SizeKb { get; set; }
    public double AvgObjSizeBytes { get; set; }
}

