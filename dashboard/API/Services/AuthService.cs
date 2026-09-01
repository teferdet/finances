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

    public AuthService(IConfiguration configuration, MongoContext mongoContext)
    {
        _configuration = configuration;
        _mongoContext = mongoContext;
    }

    public async Task<(bool Success, string Message)> RequestOtpAsync(OtpRequestDto request, string ipAddress)
    {
        
        var adminIdsStr = _configuration["BOT_ADMIN_IDS"];
        if (!string.IsNullOrEmpty(adminIdsStr))
        {
            var adminIds = adminIdsStr
                .Replace("[", "")
                .Replace("]", "")
                .Split(',')
                .Select(id => id.Trim())
                .ToList();
            if (!adminIds.Contains(request.TelegramId.ToString()))
            {
                return (false, "This Telegram ID is not authorized as an admin.");
            }
        }

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

        using var client = new HttpClient();
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
        var expirationTime = DateTime.UtcNow.AddMinutes(-5);
        var otpsCol = _mongoContext.Database.GetCollection<BsonDocument>("Otps");
        var filter = Builders<BsonDocument>.Filter.Eq("telegramId", request.TelegramId)
                   & Builders<BsonDocument>.Filter.Eq("otp", request.Otp)
                   & Builders<BsonDocument>.Filter.Eq("used", false)
                   & Builders<BsonDocument>.Filter.Gt("createdAt", expirationTime);

        var otpDoc = await otpsCol.Find(filter).FirstOrDefaultAsync();

        if (otpDoc == null)
        {
            return (false, string.Empty, "Invalid or expired OTP");
        }

        
        var updateFilter = Builders<BsonDocument>.Filter.Eq("_id", otpDoc["_id"]);
        await otpsCol.UpdateOneAsync(updateFilter, Builders<BsonDocument>.Update.Set("used", true));
        
        
        var token = GenerateJwtToken(request.TelegramId);
        return (true, token, string.Empty);
    }

    private string GenerateJwtToken(long telegramId)
    {
        var secretKey = _configuration["JWT_SECRET"] 
            ?? _configuration["DASHBOARD_SECRET_KEY"]
            ?? "ThisIsADefaultSecretKeyForDevelopmentOnly123!";

        if (string.IsNullOrWhiteSpace(secretKey) || secretKey.Length < 32)
        {
            throw new InvalidOperationException("JWT_SECRET (or DASHBOARD_SECRET_KEY) is not configured or is too short (minimum 32 characters required).");
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
