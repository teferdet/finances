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
    public IActionResult GetBotStats()
    {
        return Ok(new
        {
            serviceStatus = "running",
            startedAt = DateTime.UtcNow.AddDays(-1).ToString("O"),
            botRamMb = 150,
            botCpuPct = 5.0,
            botPid = 1234,
            botThreads = 10,
            sysRamUsedGb = 2.5,
            sysRamTotalGb = 8.0,
            sysRamPct = 31.0,
            sysCpuPct = 15.0,
            sysCpuCores = 4,
            loadAvg1m = 0.5,
            loadAvg5m = 0.6,
            diskUsedGb = 20.0,
            diskTotalGb = 100.0,
            diskPct = 20.0,
            os = "Linux",
            pythonVersion = "3.11.0",
            hostname = "docker-node",
            botVersion = "2.0.0"
        });
    }

    // GET /api/stats/parser
    [HttpGet("parser")]
    public IActionResult GetParserStats()
    {
        return Ok(new
        {
            fiat   = new { count = 10, lastUpdated = DateTime.UtcNow.ToString("O") },
            crypto = new { lastUpdated = DateTime.UtcNow.ToString("O") },
            stocks = new { lastUpdated = DateTime.UtcNow.ToString("O") },
            parserErrors = new List<object>(),
            cyclesToday = 24
        });
    }

    // GET /api/stats/alerts
    [HttpGet("alerts")]
    public IActionResult GetAlertsStats()
    {
        return Ok(new
        {
            total = 100,
            active = 50,
            triggered = 10,
            topCurrencies = new List<object> { new { currency = "BTC", count = 5 } }
        });
    }

    // GET /api/stats/groups
    [HttpGet("groups")]
    public IActionResult GetGroupsStats()
    {
        return Ok(new
        {
            total = 50,
            active = 40,
            inactive = 10,
            recent = new List<object>()
        });
    }

    // GET /api/stats/errors
    [HttpGet("errors")]
    public IActionResult GetErrors()
    {
        return Ok(new { errors = new List<object>() });
    }
}
