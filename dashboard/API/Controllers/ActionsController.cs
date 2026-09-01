using System.Diagnostics;
using API.Repositories;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using MongoDB.Bson;
using MongoDB.Driver;

namespace API.Controllers;

[ApiController]
[Route("api/actions")]
[Authorize]
public class ActionsController : ControllerBase
{
    private readonly MongoContext _mongoContext;
    private readonly IConfiguration _config;

    public ActionsController(MongoContext mongoContext, IConfiguration config)
    {
        _mongoContext = mongoContext;
        _config = config;
    }

    // POST /api/actions/restart
    [HttpPost("restart")]
    public async Task<IActionResult> RestartService()
    {
        try
        {
            var process = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName               = "sudo",
                    Arguments              = "systemctl restart finances-bot.service",
                    RedirectStandardOutput = true,
                    RedirectStandardError  = true,
                    UseShellExecute        = false,
                    CreateNoWindow         = true,
                }
            };

            process.Start();
            await process.WaitForExitAsync();

            if (process.ExitCode != 0)
            {
                var error = await process.StandardError.ReadToEndAsync();
                return StatusCode(500, new { ok = false, error = $"Restart failed: {error}" });
            }

            return Ok(new { ok = true, message = "Bot restarted successfully" });
        }
        catch (Exception ex)
        {
            return StatusCode(500, new { ok = false, error = ex.Message });
        }
    }

    // POST /api/actions/clear-otps
    /// <summary>
    /// Delete all expired (used or older than 10 min) OTP records from MongoDB.
    /// </summary>
    [HttpPost("clear-otps")]
    public async Task<IActionResult> ClearOtps()
    {
        var otpsCol  = _mongoContext.Database.GetCollection<BsonDocument>("Otps");
        var cutoff   = DateTime.UtcNow.AddMinutes(-10);

        var filter = Builders<BsonDocument>.Filter.Or(
            Builders<BsonDocument>.Filter.Eq("used", true),
            Builders<BsonDocument>.Filter.Lt("createdAt", cutoff)
        );

        var result = await otpsCol.DeleteManyAsync(filter);

        return Ok(new
        {
            ok      = true,
            deleted = result.DeletedCount,
            message = $"{result.DeletedCount} expired OTP(s) deleted."
        });
    }

    // GET /api/actions/logs?source=api&lines=100
    /// <summary>
    /// Return the last N lines from the API or bot log file.
    /// source: "api" (default) | "bot"
    /// lines: 10–500 (default 100)
    /// </summary>
    [HttpGet("logs")]
    public IActionResult GetLogs(
        [FromQuery] string source = "api",
        [FromQuery] int lines = 100)
    {
        lines = Math.Clamp(lines, 10, 500);

        var logDir = "/app/logs";
        var fileName = source == "bot" ? "bot" : "api";

        // Find the most recent rolling log file (Serilog appends date)
        string? logPath = null;
        if (Directory.Exists(logDir))
        {
            logPath = Directory.GetFiles(logDir, $"{fileName}*.log")
                .OrderByDescending(f => f)
                .FirstOrDefault();
        }

        if (logPath == null || !System.IO.File.Exists(logPath))
        {
            return Ok(new { ok = true, source, lines = 0, content = new string[0] });
        }

        // Read tail of file safely (file may be locked by logger)
        string[] tail;
        try
        {
            using var fs     = new FileStream(logPath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
            using var reader = new StreamReader(fs);
            var allLines     = new List<string>();
            string? line;
            while ((line = reader.ReadLine()) != null)
                allLines.Add(line);

            tail = allLines.Count <= lines
                ? allLines.ToArray()
                : allLines.Skip(allLines.Count - lines).ToArray();
        }
        catch (Exception ex)
        {
            return StatusCode(500, new { ok = false, error = $"Could not read log: {ex.Message}" });
        }

        return Ok(new
        {
            ok      = true,
            source,
            file    = Path.GetFileName(logPath),
            lines   = tail.Length,
            content = tail,
        });
    }
}
