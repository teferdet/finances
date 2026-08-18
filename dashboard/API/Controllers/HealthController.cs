using API.Repositories;
using Microsoft.AspNetCore.Mvc;

namespace API.Controllers;

[ApiController]
[Route("api/health")]
public class HealthController : ControllerBase
{
    private readonly MongoContext _mongoContext;

    public HealthController(MongoContext mongoContext)
    {
        _mongoContext = mongoContext;
    }

    [HttpGet]
    public async Task<IActionResult> Get()
    {
        var isDbAlive = await _mongoContext.PingAsync();
        
        if (isDbAlive)
        {
            // The frontend and deploy-dashboard.yml health check expect "status": "ok"
            return Ok(new { status = "ok", database = "connected" });
        }
        
        return StatusCode(503, new { status = "error", database = "disconnected" });
    }
}
