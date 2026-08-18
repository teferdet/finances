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

    [HttpGet("overview")]
    public async Task<IActionResult> GetOverview()
    {
        var result = await _statsService.GetOverviewAsync();
        return Ok(result);
    }

    [HttpGet("activity")]
    public async Task<IActionResult> GetActivity([FromQuery] int days = 30)
    {
        var result = await _statsService.GetActivityChartAsync(Math.Clamp(days, 7, 90));
        return Ok(result);
    }

    [HttpGet("users")]
    public async Task<IActionResult> GetUsers()
    {
        var result = await _statsService.GetUserStatsAsync();
        return Ok(result);
    }

    [HttpGet("database")]
    public async Task<IActionResult> GetDatabaseStats()
    {
        var result = await _statsService.GetDatabaseStatsAsync();
        return Ok(result);
    }

    
    [HttpGet("bot")]
    public IActionResult GetBotStats()
    {
        return Ok(new { 
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

    [HttpGet("parser")]
    public IActionResult GetParserStats()
    {
        return Ok(new { 
            fiat = new { count = 10, lastUpdated = DateTime.UtcNow.ToString("O") },
            crypto = new { lastUpdated = DateTime.UtcNow.ToString("O") },
            stocks = new { lastUpdated = DateTime.UtcNow.ToString("O") },
            parserErrors = new List<object>(),
            cyclesToday = 24
        });
    }

    [HttpGet("alerts")]
    public IActionResult GetAlertsStats()
    {
        return Ok(new { 
            total = 100, 
            active = 50, 
            triggered = 10,
            topCurrencies = new List<object> { new { currency = "BTC", count = 5 } }
        });
    }

    [HttpGet("groups")]
    public IActionResult GetGroupsStats()
    {
        return Ok(new { 
            total = 50, 
            active = 40, 
            inactive = 10,
            recent = new List<object>()
        });
    }

    [HttpGet("errors")]
    public IActionResult GetErrors()
    {
        return Ok(new { errors = new List<object>() });
    }
}
