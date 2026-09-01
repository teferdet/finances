using API.Models.Responses;
using API.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace API.Controllers;

[ApiController]
[Route("api/stats")]
[Authorize]
public class StatsController : ControllerBase
{
    private readonly StatsService _statsService;

    public StatsController(StatsService statsService)
    {
        _statsService = statsService;
    }

    // GET /api/stats/overview
    [HttpGet("overview")]
    public async Task<IActionResult> GetOverview()
    {
        var result = await _statsService.GetOverviewAsync();
        return Ok(result);
    }

    // GET /api/stats/activity?days=30
    [HttpGet("activity")]
    public async Task<IActionResult> GetActivity([FromQuery] int days = 30)
    {
        var result = await _statsService.GetActivityChartAsync(Math.Clamp(days, 7, 90));
        return Ok(result);
    }

    /// <summary>
    /// GET /api/stats/users
    ///   ?page=1          — page number (default 1)
    ///   &amp;limit=50    — items per page (1–200, default 50)
    ///   &amp;search=     — filter by username, name, or numeric Telegram ID
    ///   &amp;language=uk — filter by language code
    ///   &amp;premium=true— filter by premium status
    ///   &amp;sort=last_active|requests|premium|language
    ///   &amp;order=desc|asc
    /// </summary>
    [HttpGet("users")]
    public async Task<IActionResult> GetUsers(
        [FromQuery] int page = 1,
        [FromQuery] int limit = 50,
        [FromQuery] string? search = null,
        [FromQuery] string? language = null,
        [FromQuery] bool? premium = null,
        [FromQuery] string sort = "last_active",
        [FromQuery] string order = "desc")
    {
        var validSorts = new[] { "last_active", "requests", "premium", "language" };
        if (!validSorts.Contains(sort)) sort = "last_active";
        if (order != "asc") order = "desc";

        var result = await _statsService.GetUserStatsAsync(page, limit, search, language, premium, sort, order);
        return Ok(result);
    }

    // GET /api/stats/database
    [HttpGet("database")]
    public async Task<IActionResult> GetDatabaseStats()
    {
        var result = await _statsService.GetDatabaseStatsAsync();
        return Ok(result);
    }

    // GET /api/stats/bot
    [HttpGet("bot")]
    public async Task<IActionResult> GetBotStats()
    {
        var result = await _statsService.GetBotStatsAsync();
        return Ok(result);
    }

    // GET /api/stats/parser
    [HttpGet("parser")]
    public async Task<IActionResult> GetParserStats()
    {
        var result = await _statsService.GetParserStatsAsync();
        return Ok(result);
    }

    // GET /api/stats/alerts
    [HttpGet("alerts")]
    public async Task<IActionResult> GetAlertsStats()
    {
        var result = await _statsService.GetAlertsStatsAsync();
        return Ok(result);
    }

    // GET /api/stats/groups
    [HttpGet("groups")]
    public async Task<IActionResult> GetGroupsStats()
    {
        var result = await _statsService.GetGroupsStatsAsync();
        return Ok(result);
    }

    // GET /api/stats/errors
    [HttpGet("errors")]
    public async Task<IActionResult> GetErrors()
    {
        var result = await _statsService.GetErrorsAsync();
        return Ok(new { errors = result });
    }
}
