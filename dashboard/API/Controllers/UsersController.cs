using System.Text;
using System.Text.Json;
using API.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace API.Controllers;

/// <summary>
/// Admin-level user management: per-user data export (JSON + CSV) and hard delete.
/// All endpoints require a valid JWT session.
/// </summary>
[ApiController]
[Route("api/users")]
[Authorize]
public class UsersController : ControllerBase
{
    private readonly UserDataService _userDataService;
    private readonly ILogger<UsersController> _logger;

    public UsersController(UserDataService userDataService, ILogger<UsersController> logger)
    {
        _userDataService = userDataService;
        _logger = logger;
    }

    // ── GET /api/users/{id}/export ────────────────────────────────────────────
    /// <summary>
    /// Export all data of a single user as a JSON file.
    /// Includes: profile, settings, portfolio, alerts, API key metadata (no secrets).
    /// </summary>
    [HttpGet("{id:long}/export")]
    public async Task<IActionResult> ExportUserJson(long id)
    {
        var export = await _userDataService.ExportUserAsync(id);
        if (export == null)
            return NotFound(new { ok = false, error = $"User {id} not found." });

        var json = JsonSerializer.Serialize(export, new JsonSerializerOptions
        {
            WriteIndented = true,
            PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        });

        var bytes = Encoding.UTF8.GetBytes(json);
        var fileName = $"user_{id}_export_{DateTime.UtcNow:yyyyMMdd_HHmmss}.json";

        _logger.LogInformation("User {UserId} data exported as JSON by dashboard admin", id);

        return File(bytes, "application/json", fileName);
    }

    // ── GET /api/users/{id}/export/csv ────────────────────────────────────────
    /// <summary>
    /// Export all data of a single user as a human-readable CSV file.
    /// Each section (profile, portfolio, alerts, API keys) is a separate block.
    /// </summary>
    [HttpGet("{id:long}/export/csv")]
    public async Task<IActionResult> ExportUserCsv(long id)
    {
        var export = await _userDataService.ExportUserAsync(id);
        if (export == null)
            return NotFound(new { ok = false, error = $"User {id} not found." });

        var sb = new StringBuilder();

        // Profile
        sb.AppendLine("# PROFILE");
        sb.AppendLine("field,value");
        sb.AppendLine($"id,{export.Id}");
        sb.AppendLine($"name,{CsvEscape(export.Name)}");
        sb.AppendLine($"username,{CsvEscape(export.Username)}");
        sb.AppendLine($"language,{CsvEscape(export.Language)}");
        sb.AppendLine($"premium,{export.Premium}");
        sb.AppendLine($"sign_up,{CsvEscape(export.SignUp)}");
        sb.AppendLine($"last_active,{CsvEscape(export.LastActive)}");
        sb.AppendLine($"base_currency,{CsvEscape(export.BaseCurrency)}");
        sb.AppendLine($"rate_mode,{CsvEscape(export.RateMode)}");
        sb.AppendLine($"portfolio_view,{CsvEscape(export.PortfolioView)}");
        sb.AppendLine($"number_format,{CsvEscape(export.NumberFormat)}");
        sb.AppendLine($"weekly_digest,{export.WeeklyDigest}");
        sb.AppendLine($"big_buttons,{export.BigButtons}");
        sb.AppendLine($"volatility_threshold,{export.VolatilityThreshold}");
        sb.AppendLine($"total_requests,{export.Stats.TotalRequests}");
        sb.AppendLine($"fiat_currencies,{CsvEscape(string.Join(";", export.FiatCurrencies))}");
        sb.AppendLine($"crypto_currencies,{CsvEscape(string.Join(";", export.CryptoCurrencies))}");
        sb.AppendLine($"stocks,{CsvEscape(string.Join(";", export.Stocks))}");
        sb.AppendLine();

        // Portfolio
        sb.AppendLine("# PORTFOLIO");
        sb.AppendLine("asset_type,ticker,amount,buy_price_usd");
        foreach (var lot in export.PortfolioCrypto)
            sb.AppendLine($"crypto,{CsvEscape(lot.Ticker)},{lot.Amount},{lot.BuyPriceUsd?.ToString() ?? ""}");
        foreach (var lot in export.PortfolioStocks)
            sb.AppendLine($"stock,{CsvEscape(lot.Ticker)},{lot.Amount},{lot.BuyPriceUsd?.ToString() ?? ""}");
        foreach (var lot in export.PortfolioFiat)
            sb.AppendLine($"fiat,{CsvEscape(lot.Ticker)},{lot.Amount},{lot.BuyPriceUsd?.ToString() ?? ""}");
        sb.AppendLine();

        // Alerts
        sb.AppendLine("# ALERTS");
        sb.AppendLine("id,currency_from,currency_to,condition,target_price,triggered,created_at");
        foreach (var a in export.Alerts)
            sb.AppendLine($"{CsvEscape(a.Id)},{CsvEscape(a.CurrencyFrom)},{CsvEscape(a.CurrencyTo)},{CsvEscape(a.Condition)},{a.TargetPrice},{a.Triggered},{CsvEscape(a.CreatedAt)}");
        sb.AppendLine();

        // API Keys (no secrets)
        sb.AppendLine("# API KEYS (secrets excluded for security)");
        sb.AppendLine("exchange,last_sync");
        foreach (var k in export.ApiKeys)
            sb.AppendLine($"{CsvEscape(k.Exchange)},{CsvEscape(k.LastSync)}");

        var bytes = Encoding.UTF8.GetBytes(sb.ToString());
        var fileName = $"user_{id}_export_{DateTime.UtcNow:yyyyMMdd_HHmmss}.csv";

        _logger.LogInformation("User {UserId} data exported as CSV by dashboard admin", id);

        return File(bytes, "text/csv", fileName);
    }

    // ── DELETE /api/users/{id} ────────────────────────────────────────────────
    /// <summary>
    /// Hard-delete a user and ALL associated data:
    /// Users, Alerts, ApiKeys, Otps.
    /// This action is irreversible.
    /// </summary>
    [HttpDelete("{id:long}")]
    public async Task<IActionResult> DeleteUser(long id)
    {
        var result = await _userDataService.DeleteUserAsync(id);
        if (result == null)
            return NotFound(new { ok = false, error = $"User {id} not found." });

        _logger.LogWarning(
            "User {UserId} hard-deleted by dashboard admin. " +
            "Alerts: {Alerts}, ApiKeys: {Keys}, Otps: {Otps}",
            id, result.AlertsDeleted, result.ApiKeysDeleted, result.OtpsDeleted);

        return Ok(result);
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    /// <summary>CSV-safe field: wraps in quotes if value contains comma, quote, or newline.</summary>
    private static string CsvEscape(string? value)
    {
        if (string.IsNullOrEmpty(value)) return string.Empty;
        if (value.Contains(',') || value.Contains('"') || value.Contains('\n'))
            return $"\"{value.Replace("\"", "\"\"")}\"";
        return value;
    }
}
