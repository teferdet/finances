using API.Models.Requests;
using API.Repositories;
using API.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using MongoDB.Bson;
using MongoDB.Driver;

namespace API.Controllers;

[ApiController]
[Route("api/auth")]
public class AuthController : ControllerBase
{
    private readonly AuthService _authService;
    private readonly MongoContext _mongoContext;

    public AuthController(AuthService authService, MongoContext mongoContext)
    {
        _authService = authService;
        _mongoContext = mongoContext;
    }

    [HttpPost("request-otp")]
    [EnableRateLimiting("otp")]  // Fix #1: max 5 requests per 5 minutes per IP
    public async Task<IActionResult> RequestOtp([FromBody] OtpRequestDto request)
    {
        var ipAddress = HttpContext.Connection.RemoteIpAddress?.ToString() ?? "0.0.0.0";

        var (success, message) = await _authService.RequestOtpAsync(request, ipAddress);

        if (!success)
        {
            return BadRequest(new { ok = false, error = message });
        }

        return Ok(new { ok = true, message = message });
    }

    [HttpPost("verify-otp")]
    [EnableRateLimiting("otp")]  // Fix #1: same 5/5-min limit; DB-layer attempt counter adds depth
    public async Task<IActionResult> VerifyOtp([FromBody] OtpVerifyDto request)
    {
        var ipAddress = HttpContext.Connection.RemoteIpAddress?.ToString() ?? "0.0.0.0";

        var (success, token, error) = await _authService.VerifyOtpAsync(request, ipAddress);

        if (!success)
        {
            return Unauthorized(new { ok = false, error = error });
        }

        
        // Secure flag only when actually on HTTPS (direct TLS or behind nginx with X-Forwarded-Proto).
        // Without this, browsers silently drop the cookie over HTTP → 401 on every API call.
        var isHttps = Request.IsHttps ||
                      Request.Headers["X-Forwarded-Proto"].ToString() == "https";

        var cookieOptions = new CookieOptions
        {
            HttpOnly = true,
            SameSite = SameSiteMode.Strict,
            Secure = isHttps,
            MaxAge = TimeSpan.FromDays(7),
            Path = "/"
        };
        
        Response.Cookies.Append("dash_session", token, cookieOptions);

        return Ok(new { ok = true });
    }

    [HttpPost("logout")]
    public IActionResult Logout()
    {
        var isHttpsLogout = Request.IsHttps ||
                            Request.Headers["X-Forwarded-Proto"].ToString() == "https";

        Response.Cookies.Delete("dash_session", new CookieOptions
        {
            Path = "/",
            HttpOnly = true,
            SameSite = SameSiteMode.Strict,
            Secure = isHttpsLogout
        });
        return Ok(new { ok = true });
    }

    [HttpGet("check-status")]
    public async Task<IActionResult> CheckStatus([FromQuery] string req_id)
    {
        // M-5 fix: reads the real approval status from the dash_auth_requests collection.
        // The Python bot's cb_dash_auth callback sets status to "approved" or "blocked"
        // when the admin clicks the inline approval button sent via Telegram.
        if (string.IsNullOrWhiteSpace(req_id))
            return BadRequest(new { ok = false, error = "req_id is required" });

        var col = _mongoContext.Database.GetCollection<BsonDocument>("dash_auth_requests");
        var doc = await col.Find(Builders<BsonDocument>.Filter.Eq("_id", req_id))
                           .FirstOrDefaultAsync();

        string status = "pending";
        if (doc != null && doc.TryGetValue("status", out var statusVal))
            status = statusVal.AsString;

        return Ok(new { ok = true, status });
    }
}
