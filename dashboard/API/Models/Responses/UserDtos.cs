namespace API.Models.Responses;

/// <summary>Full details of a single user exported from MongoDB.</summary>
public class UserExportDto
{
    public long Id { get; set; }
    public string? Name { get; set; }
    public string? Username { get; set; }
    public string? Language { get; set; }
    public bool Premium { get; set; }
    public string? SignUp { get; set; }
    public string? LastActive { get; set; }

    // Settings
    public List<string> FiatCurrencies { get; set; } = new();
    public List<string> CryptoCurrencies { get; set; } = new();
    public List<string> Stocks { get; set; } = new();
    public string? BaseCurrency { get; set; }
    public string? RateMode { get; set; }
    public string? PortfolioView { get; set; }
    public string? NumberFormat { get; set; }
    public bool WeeklyDigest { get; set; }
    public bool BigButtons { get; set; }
    public int VolatilityThreshold { get; set; }

    // Portfolio
    public List<PortfolioLotDto> PortfolioCrypto { get; set; } = new();
    public List<PortfolioLotDto> PortfolioStocks { get; set; } = new();
    public List<PortfolioLotDto> PortfolioFiat { get; set; } = new();

    // Related data
    public List<AlertDto> Alerts { get; set; } = new();
    public List<ApiKeyDto> ApiKeys { get; set; } = new();

    // Stats
    public UserStatsFieldDto Stats { get; set; } = new();

    // Metadata
    public string ExportedAt { get; set; } = DateTime.UtcNow.ToString("O");
}

public class PortfolioLotDto
{
    public string Ticker { get; set; } = string.Empty;
    public double Amount { get; set; }
    public double? BuyPriceUsd { get; set; }
}

public class AlertDto
{
    public string Id { get; set; } = string.Empty;
    public string CurrencyFrom { get; set; } = string.Empty;
    public string CurrencyTo { get; set; } = string.Empty;
    public string Condition { get; set; } = string.Empty;
    public double TargetPrice { get; set; }
    public bool Triggered { get; set; }
    public string? CreatedAt { get; set; }
}

public class ApiKeyDto
{
    public string Exchange { get; set; } = string.Empty;
    public string? LastSync { get; set; }
    // API key/secret are intentionally omitted for security
}

public class UserStatsFieldDto
{
    public int TotalRequests { get; set; }
    public int RequestsToday { get; set; }
}

/// <summary>Summary returned after deleting a user.</summary>
public class UserDeleteResultDto
{
    public bool Ok { get; set; }
    public long UserId { get; set; }
    public int AlertsDeleted { get; set; }
    public int ApiKeysDeleted { get; set; }
    public int OtpsDeleted { get; set; }
    public string Message { get; set; } = string.Empty;
}
