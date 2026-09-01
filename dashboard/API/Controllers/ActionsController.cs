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

    // H-4: Per-token sliding-window rate limiter for the sensitive log endpoint
    // (max 10 requests per 60 seconds per JWT subject).
    private static readonly System.Collections.Concurrent.ConcurrentDictionary<string, Queue<DateTime>>
        _logRequests = new();

    private static bool IsLogRateLimited(string subject)
    {
        var now = DateTime.UtcNow;
        var queue = _logRequests.GetOrAdd(subject, _ => new Queue<DateTime>());
        lock (queue)
        {
            while (queue.Count > 0 && (now - queue.Peek()).TotalSeconds > 60)
                queue.Dequeue();
            if (queue.Count >= 10)
                return true;
            queue.Enqueue(now);
            return false;
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
        // H-4 fix: rate-limit this endpoint to prevent continuous log scraping
        // by a stolen JWT (max 10 requests per minute per token subject).
        var subject = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value ?? "unknown";
        if (IsLogRateLimited(subject))
            return StatusCode(429, new { ok = false, error = "Too many log requests. Maximum 10 per minute." });

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
