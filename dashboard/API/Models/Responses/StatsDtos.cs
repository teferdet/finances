using System.Text.Json.Serialization;

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

// ── Bot Status ────────────────────────────────────────────────────────────────

public class BotStatusDto
{
    [JsonPropertyName("service_status")]
    public string ServiceStatus { get; set; } = "active";

    [JsonPropertyName("started_at")]
    public string? StartedAt { get; set; }

    [JsonPropertyName("bot_ram_mb")]
    public double? BotRamMb { get; set; }

    [JsonPropertyName("bot_cpu_pct")]
    public double? BotCpuPct { get; set; }

    [JsonPropertyName("bot_pid")]
    public int? BotPid { get; set; }

    [JsonPropertyName("bot_threads")]
    public int? BotThreads { get; set; }

    [JsonPropertyName("sys_ram_used_gb")]
    public double SysRamUsedGb { get; set; }

    [JsonPropertyName("sys_ram_total_gb")]
    public double SysRamTotalGb { get; set; }

    [JsonPropertyName("sys_ram_pct")]
    public double SysRamPct { get; set; }

    [JsonPropertyName("sys_cpu_pct")]
    public double SysCpuPct { get; set; }

    [JsonPropertyName("sys_cpu_cores")]
    public int SysCpuCores { get; set; }

    [JsonPropertyName("load_avg_1m")]
    public double LoadAvg1m { get; set; }

    [JsonPropertyName("load_avg_5m")]
    public double LoadAvg5m { get; set; }

    [JsonPropertyName("disk_used_gb")]
    public double DiskUsedGb { get; set; }

    [JsonPropertyName("disk_total_gb")]
    public double DiskTotalGb { get; set; }

    [JsonPropertyName("disk_pct")]
    public double DiskPct { get; set; }

    [JsonPropertyName("os")]
    public string Os { get; set; } = string.Empty;

    [JsonPropertyName("python_version")]
    public string PythonVersion { get; set; } = "3.11+";

    [JsonPropertyName("hostname")]
    public string Hostname { get; set; } = string.Empty;

    [JsonPropertyName("bot_version")]
    public string BotVersion { get; set; } = "2.0.0";
}

// ── Parser Status ─────────────────────────────────────────────────────────────

public class ParserStatsDto
{
    [JsonPropertyName("fiat")]
    public ParserSubStatDto Fiat { get; set; } = new();

    [JsonPropertyName("crypto")]
    public ParserSubStatDto Crypto { get; set; } = new();

    [JsonPropertyName("stocks")]
    public ParserSubStatDto Stocks { get; set; } = new();

    [JsonPropertyName("parser_errors")]
    public List<ParserErrorDto> ParserErrors { get; set; } = new();

    [JsonPropertyName("cycles_today")]
    public int CyclesToday { get; set; }
}

public class ParserSubStatDto
{
    [JsonPropertyName("count")]
    public int? Count { get; set; }

    [JsonPropertyName("last_updated")]
    public string? LastUpdated { get; set; }
}

public class ParserErrorDto
{
    [JsonPropertyName("source")]
    public string Source { get; set; } = string.Empty;

    [JsonPropertyName("count")]
    public int Count { get; set; }

    [JsonPropertyName("last_error")]
    public string LastError { get; set; } = string.Empty;

    [JsonPropertyName("last_seen")]
    public string? LastSeen { get; set; }
}

// ── Alerts Stats ──────────────────────────────────────────────────────────────

public class AlertsStatsDto
{
    [JsonPropertyName("total")]
    public long Total { get; set; }

    [JsonPropertyName("active")]
    public long Active { get; set; }

    [JsonPropertyName("triggered")]
    public long Triggered { get; set; }

    [JsonPropertyName("top_currencies")]
    public List<CurrencyCountDto> TopCurrencies { get; set; } = new();
}

public class CurrencyCountDto
{
    [JsonPropertyName("currency")]
    public string Currency { get; set; } = string.Empty;

    [JsonPropertyName("count")]
    public int Count { get; set; }
}

// ── Groups Stats ──────────────────────────────────────────────────────────────

public class GroupsStatsDto
{
    [JsonPropertyName("total")]
    public long Total { get; set; }

    [JsonPropertyName("active")]
    public long Active { get; set; }

    [JsonPropertyName("inactive")]
    public long Inactive { get; set; }

    [JsonPropertyName("recent")]
    public List<RecentGroupDto> Recent { get; set; } = new();
}

public class RecentGroupDto
{
    [JsonPropertyName("id")]
    public long Id { get; set; }

    [JsonPropertyName("title")]
    public string Title { get; set; } = string.Empty;

    [JsonPropertyName("member_count")]
    public int MemberCount { get; set; }

    [JsonPropertyName("joined_at")]
    public string? JoinedAt { get; set; }
}

// ── Error Log Item ────────────────────────────────────────────────────────────

public class ErrorLogItemDto
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("source")]
    public string Source { get; set; } = string.Empty;

    [JsonPropertyName("message")]
    public string Message { get; set; } = string.Empty;

    [JsonPropertyName("timestamp")]
    public string Timestamp { get; set; } = string.Empty;

    [JsonPropertyName("count")]
    public int Count { get; set; } = 1;
}

