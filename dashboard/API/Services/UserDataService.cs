using API.Models.Responses;
using API.Repositories;
using MongoDB.Bson;
using MongoDB.Driver;

namespace API.Services;

/// <summary>
/// Handles per-user data operations: full export and hard delete with cascade.
/// </summary>
public class UserDataService
{
    private readonly MongoContext _mongoContext;

    public UserDataService(MongoContext mongoContext)
    {
        _mongoContext = mongoContext;
    }

    // ── Export ────────────────────────────────────────────────────────────────

    /// <summary>
    /// Exports all data about a user from every collection they appear in.
    /// Returns null if the user does not exist.
    /// </summary>
    public async Task<UserExportDto?> ExportUserAsync(long userId)
    {
        var db = _mongoContext.Database;
        var usersCol  = db.GetCollection<BsonDocument>("Users");
        var alertsCol = db.GetCollection<BsonDocument>("Alerts");
        var keysCol   = db.GetCollection<BsonDocument>("ApiKeys");

        // ── User document ────────────────────────────────────────────────────
        var user = await usersCol.Find(Builders<BsonDocument>.Filter.Eq("_id", userId))
                                 .FirstOrDefaultAsync();
        if (user == null) return null;

        var dto = new UserExportDto
        {
            Id         = userId,
            Name       = GetStr(user, "Name"),
            Username   = GetStr(user, "Username"),
            Language   = GetStr(user, "Language"),
            Premium    = GetBool(user, "Premium"),
            SignUp     = GetStr(user, "Sign up"),
            LastActive = GetDateStr(user, "last_active"),

            // Settings
            FiatCurrencies      = GetStringList(user, "Fiat currency"),
            CryptoCurrencies    = GetStringList(user, "Crypto currency"),
            Stocks              = GetStringList(user, "Stocks"),
            BaseCurrency        = GetStr(user, "BaseCurrency"),
            RateMode            = GetStr(user, "RateMode"),
            PortfolioView       = GetStr(user, "PortfolioView"),
            NumberFormat        = GetStr(user, "NumberFormat"),
            WeeklyDigest        = GetBool(user, "WeeklyDigest", defaultVal: true),
            BigButtons          = GetBool(user, "BigButtons"),
            VolatilityThreshold = GetInt(user, "VolatilityThreshold", 5),
        };

        // ── Portfolio ────────────────────────────────────────────────────────
        if (user.Contains("portfolio") && user["portfolio"].IsBsonDocument)
        {
            var portfolio = user["portfolio"].AsBsonDocument;
            dto.PortfolioCrypto = ExtractPortfolioSection(portfolio, "crypto");
            dto.PortfolioStocks = ExtractPortfolioSection(portfolio, "stock");
            dto.PortfolioFiat   = ExtractPortfolioSection(portfolio, "fiat");
        }

        // ── Alerts ───────────────────────────────────────────────────────────
        var alertFilter = Builders<BsonDocument>.Filter.Eq("user_id", userId);
        var alertDocs   = await alertsCol.Find(alertFilter).ToListAsync();
        dto.Alerts = alertDocs.Select(a => new AlertDto
        {
            Id           = a.GetValue("_id", BsonNull.Value).ToString() ?? string.Empty,
            CurrencyFrom = GetStr(a, "currency_from") ?? string.Empty,
            CurrencyTo   = GetStr(a, "currency_to")   ?? string.Empty,
            Condition    = GetStr(a, "condition")      ?? string.Empty,
            TargetPrice  = GetDouble(a, "target_price"),
            Triggered    = GetBool(a, "triggered"),
            CreatedAt    = GetDateStr(a, "created_at"),
        }).ToList();

        // ── API Keys ─────────────────────────────────────────────────────────
        var keyFilter = Builders<BsonDocument>.Filter.Eq("user_id", userId);
        var keyDocs   = await keysCol.Find(keyFilter).ToListAsync();
        dto.ApiKeys = keyDocs.Select(k => new ApiKeyDto
        {
            Exchange = GetStr(k, "exchange") ?? string.Empty,
            LastSync = GetDateStr(k, "last_sync"),
            // api_key and api_secret intentionally excluded
        }).ToList();

        // ── Stats ────────────────────────────────────────────────────────────
        if (user.Contains("stats") && user["stats"].IsBsonDocument)
        {
            var stats = user["stats"].AsBsonDocument;
            dto.Stats = new UserStatsFieldDto
            {
                TotalRequests  = GetInt(stats, "total_requests"),
                RequestsToday  = GetInt(stats, "requests_today"),
            };
        }

        return dto;
    }

    // ── Delete ────────────────────────────────────────────────────────────────

    /// <summary>
    /// Hard-deletes a user and ALL their associated data from every collection.
    /// Returns null if the user does not exist.
    /// </summary>
    public async Task<UserDeleteResultDto?> DeleteUserAsync(long userId)
    {
        var db = _mongoContext.Database;
        var usersCol  = db.GetCollection<BsonDocument>("Users");
        var alertsCol = db.GetCollection<BsonDocument>("Alerts");
        var keysCol   = db.GetCollection<BsonDocument>("ApiKeys");
        var otpsCol   = db.GetCollection<BsonDocument>("Otps");

        // Verify user exists before deleting anything
        var userExists = await usersCol.CountDocumentsAsync(
            Builders<BsonDocument>.Filter.Eq("_id", userId)) > 0;

        if (!userExists) return null;

        // Delete in dependency order (related first, then the user itself)
        var alertsResult = await alertsCol.DeleteManyAsync(
            Builders<BsonDocument>.Filter.Eq("user_id", userId));

        var keysResult = await keysCol.DeleteManyAsync(
            Builders<BsonDocument>.Filter.Eq("user_id", userId));

        var otpsResult = await otpsCol.DeleteManyAsync(
            Builders<BsonDocument>.Filter.Eq("telegramId", userId));

        await usersCol.DeleteOneAsync(
            Builders<BsonDocument>.Filter.Eq("_id", userId));

        return new UserDeleteResultDto
        {
            Ok             = true,
            UserId         = userId,
            AlertsDeleted  = (int)alertsResult.DeletedCount,
            ApiKeysDeleted = (int)keysResult.DeletedCount,
            OtpsDeleted    = (int)otpsResult.DeletedCount,
            Message        = $"User {userId} and all associated data deleted successfully.",
        };
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static string? GetStr(BsonDocument doc, string key)
        => doc.Contains(key) && !doc[key].IsBsonNull ? doc[key].ToString() : null;

    private static bool GetBool(BsonDocument doc, string key, bool defaultVal = false)
    {
        if (!doc.Contains(key) || doc[key].IsBsonNull) return defaultVal;
        return doc[key].IsBoolean ? doc[key].AsBoolean : defaultVal;
    }

    private static int GetInt(BsonDocument doc, string key, int defaultVal = 0)
    {
        if (!doc.Contains(key) || doc[key].IsBsonNull) return defaultVal;
        return doc[key].IsInt32 ? doc[key].AsInt32 : defaultVal;
    }

    private static double GetDouble(BsonDocument doc, string key, double defaultVal = 0)
    {
        if (!doc.Contains(key) || doc[key].IsBsonNull) return defaultVal;
        var v = doc[key];
        if (v.IsDouble) return v.AsDouble;
        if (v.IsInt32)  return v.AsInt32;
        if (v.IsInt64)  return v.AsInt64;
        return defaultVal;
    }

    private static string? GetDateStr(BsonDocument doc, string key)
    {
        if (!doc.Contains(key) || doc[key].IsBsonNull) return null;
        var v = doc[key];
        if (v.BsonType == BsonType.DateTime) return v.ToUniversalTime().ToString("O");
        return v.ToString();
    }

    private static List<string> GetStringList(BsonDocument doc, string key)
    {
        if (!doc.Contains(key) || !doc[key].IsBsonArray) return new();
        return doc[key].AsBsonArray
            .Where(x => !x.IsBsonNull)
            .Select(x => x.ToString() ?? string.Empty)
            .ToList();
    }

    private static List<PortfolioLotDto> ExtractPortfolioSection(BsonDocument portfolio, string section)
    {
        if (!portfolio.Contains(section) || !portfolio[section].IsBsonArray) return new();
        return portfolio[section].AsBsonArray
            .Where(x => x.IsBsonDocument)
            .Select(x => x.AsBsonDocument)
            .Select(lot => new PortfolioLotDto
            {
                Ticker      = GetStr(lot, "ticker")        ?? string.Empty,
                Amount      = GetDouble(lot, "amount"),
                BuyPriceUsd = lot.Contains("buy_price_usd") && !lot["buy_price_usd"].IsBsonNull
                                  ? GetDouble(lot, "buy_price_usd")
                                  : null,
            })
            .ToList();
    }
}
