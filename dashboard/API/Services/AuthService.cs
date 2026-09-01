using Microsoft.IdentityModel.Tokens;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using API.Models.Requests;
using MongoDB.Bson;
using MongoDB.Driver;
using API.Repositories;

namespace API.Services;

public class AuthService
{
    private readonly IConfiguration _configuration;
    private readonly MongoContext _mongoContext;
    private readonly IHttpClientFactory _httpClientFactory;

    public AuthService(IConfiguration configuration, MongoContext mongoContext, IHttpClientFactory httpClientFactory)
    {
        _configuration = configuration;
        _mongoContext = mongoContext;
        _httpClientFactory = httpClientFactory;
    }

    public async Task<(bool Success, string Message)> RequestOtpAsync(OtpRequestDto request, string ipAddress)
    {
        // Fix #2: fail CLOSED — if BOT_ADMIN_IDS is unset or empty, refuse all logins.
        // The previous fail-open logic allowed any Telegram ID to log in when the env
        // var was missing, silently converting admin-only access to open access.
        var adminIdsStr = _configuration["BOT_ADMIN_IDS"];
        if (string.IsNullOrWhiteSpace(adminIdsStr))
            return (false, "Admin list (BOT_ADMIN_IDS) is not configured; refusing all logins for security.");

        var adminIds = adminIdsStr
            .Replace("[", "")
            .Replace("]", "")
            .Split(',')
            .Select(id => id.Trim())
            .Where(s => s.Length > 0)
            .ToList();

        if (adminIds.Count == 0 || !adminIds.Contains(request.TelegramId.ToString()))
            return (false, "This Telegram ID is not authorized as an admin.");

        var otp = RandomNumberGenerator.GetInt32(100000, 1000000).ToString();
        
        var otpsCol = _mongoContext.Database.GetCollection<BsonDocument>("Otps");

        // Auto-cleanup: remove stale OTPs for this user (used or older than 10 min)
        var staleFilter = Builders<BsonDocument>.Filter.And(
            Builders<BsonDocument>.Filter.Eq("telegramId", request.TelegramId),
            Builders<BsonDocument>.Filter.Or(
                Builders<BsonDocument>.Filter.Eq("used", true),
                Builders<BsonDocument>.Filter.Lt("createdAt", DateTime.UtcNow.AddMinutes(-10))
            )
        );
        await otpsCol.DeleteManyAsync(staleFilter);

        await otpsCol.InsertOneAsync(new BsonDocument
        {
            { "telegramId", request.TelegramId },
            { "otp", otp },
            { "ipAddress", ipAddress },
            { "createdAt", DateTime.UtcNow },
            { "used", false }
        });
        
        
        var botToken = _configuration["BOT_TOKEN"];
        if (string.IsNullOrEmpty(botToken))
        {
            return (false, "BOT_TOKEN is not configured.");
        }

        var telegramUrl = $"https://api.telegram.org/bot{botToken}/sendMessage";
        var messageText = $"🔐 <b>Dashboard Login Request</b>\n\nYour OTP is: <code>{otp}</code>\nIP: {ipAddress}";

        var client = _httpClientFactory.CreateClient();
        var payload = new
        {
            chat_id = request.TelegramId,
            text = messageText,
            parse_mode = "HTML"
        };

        var response = await client.PostAsJsonAsync(telegramUrl, payload);
        if (!response.IsSuccessStatusCode)
        {
            return (false, "Failed to send OTP via Telegram. Please check bot token and chat ID.");
        }
        
        return (true, "OTP & Approval buttons sent via Telegram");
    }

    public async Task<(bool Success, string Token, string Error)> VerifyOtpAsync(OtpVerifyDto request, string ipAddress)
    {
        // Fix #1 (DB layer): restructured to track failed attempts per telegramId.
        // Previously the filter included the OTP value, so wrong guesses returned a generic
        // "not found" without incrementing a counter — brute force was unconstrained at the
        // database level (HTTP-layer limiter alone is bypassable via distributed IPs).
        const int MaxAttempts = 5;
        var expirationTime = DateTime.UtcNow.AddMinutes(-5);
        var otpsCol = _mongoContext.Database.GetCollection<BsonDocument>("Otps");

        // Step 1: find the active (non-expired, non-used) OTP doc for this telegramId
        var docFilter = Builders<BsonDocument>.Filter.Eq("telegramId", request.TelegramId)
                      & Builders<BsonDocument>.Filter.Eq("used", false)
                      & Builders<BsonDocument>.Filter.Gt("createdAt", expirationTime);

        var otpDoc = await otpsCol.Find(docFilter).FirstOrDefaultAsync();

        if (otpDoc == null)
            return (false, string.Empty, "Invalid or expired OTP.");

        // Step 2: check if this OTP has been locked out by too many wrong attempts
        var failedAttempts = otpDoc.TryGetValue("failedAttempts", out var fa) ? fa.ToInt32() : 0;
        if (failedAttempts >= MaxAttempts)
        {
            // Invalidate the OTP so the attacker cannot keep trying after a window reset
            await otpsCol.UpdateOneAsync(
                Builders<BsonDocument>.Filter.Eq("_id", otpDoc["_id"]),
                Builders<BsonDocument>.Update.Set("used", true));
            return (false, string.Empty, "OTP locked after too many failed attempts. Please request a new OTP.");
        }

        // Step 3: validate the OTP value
        var storedOtp = otpDoc.TryGetValue("otp", out var storedVal) ? storedVal.AsString : "";
        if (storedOtp != request.Otp)
        {
            // Increment failed attempts atomically
            await otpsCol.UpdateOneAsync(
                Builders<BsonDocument>.Filter.Eq("_id", otpDoc["_id"]),
                Builders<BsonDocument>.Update.Inc("failedAttempts", 1));
            var remaining = MaxAttempts - failedAttempts - 1;
            return (false, string.Empty, remaining > 0
                ? $"Invalid OTP. {remaining} attempt(s) remaining."
                : "Invalid OTP. No more attempts — request a new OTP.");
        }

        // Step 4: OTP is correct — mark as used and issue JWT
        await otpsCol.UpdateOneAsync(
            Builders<BsonDocument>.Filter.Eq("_id", otpDoc["_id"]),
            Builders<BsonDocument>.Update.Set("used", true));

        var token = GenerateJwtToken(request.TelegramId);
        return (true, token, string.Empty);
    }

    private string GenerateJwtToken(long telegramId)
    {
        // C-1 fix: removed hardcoded fallback secret. An absent or short JWT_SECRET now
        // causes an immediate failure rather than silently signing tokens with a known key
        // that any attacker with source-code access could use to forge valid sessions.
        var secretKey = _configuration["JWT_SECRET"]
            ?? _configuration["DASHBOARD_SECRET_KEY"]
            ?? throw new InvalidOperationException(
                "JWT_SECRET (or DASHBOARD_SECRET_KEY) is not configured. " +
                "Generate a strong random secret (min 32 chars) with: openssl rand -hex 32");

        if (string.IsNullOrWhiteSpace(secretKey) || secretKey.Length < 32)
        {
            throw new InvalidOperationException(
                "JWT_SECRET is too short (minimum 32 characters required). " +
                "Generate a new one with: openssl rand -hex 32");
        }

        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secretKey));
        var creds = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);

        var claims = new[]
        {
            new Claim(JwtRegisteredClaimNames.Sub, telegramId.ToString()),
            new Claim(ClaimTypes.NameIdentifier, telegramId.ToString()),
            new Claim(JwtRegisteredClaimNames.Jti, Guid.NewGuid().ToString())
        };

        var token = new JwtSecurityToken(
            issuer: "FinancesDashboard",
            audience: "FinancesDashboard",
            claims: claims,
            expires: DateTime.UtcNow.AddDays(7),
            signingCredentials: creds
        );

        return new JwtSecurityTokenHandler().WriteToken(token);
    }
}
