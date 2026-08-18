using API.Models.Requests;
using API.Services;
using Microsoft.AspNetCore.Mvc;

namespace API.Controllers;

[ApiController]
[Route("api/auth")]
public class AuthController : ControllerBase
{
    private readonly AuthService _authService;

    public AuthController(AuthService authService)
    {
        _authService = authService;
    }

    [HttpPost("request-otp")]
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
    public async Task<IActionResult> VerifyOtp([FromBody] OtpVerifyDto request)
    {
        var ipAddress = HttpContext.Connection.RemoteIpAddress?.ToString() ?? "0.0.0.0";

        var (success, token, error) = await _authService.VerifyOtpAsync(request, ipAddress);

        if (!success)
        {
            return Unauthorized(new { ok = false, error = error });
        }

        
        var cookieOptions = new CookieOptions
        {
            HttpOnly = true,
            SameSite = SameSiteMode.Strict,
            Secure = true, 
            MaxAge = TimeSpan.FromDays(7),
            Path = "/"
        };
        
        Response.Cookies.Append("dash_session", token, cookieOptions);

        return Ok(new { ok = true });
    }

    [HttpPost("logout")]
    public IActionResult Logout()
    {
        Response.Cookies.Delete("dash_session", new CookieOptions
        {
            Path = "/",
            HttpOnly = true,
            SameSite = SameSiteMode.Strict,
            Secure = true
        });
        return Ok(new { ok = true });
    }

    [HttpGet("check-status")]
    public IActionResult CheckStatus([FromQuery] string req_id)
    {
        
        return Ok(new { ok = true, status = "pending" });
    }
}
