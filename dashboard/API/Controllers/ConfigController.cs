using API.Models.Requests;
using API.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace API.Controllers;

[ApiController]
[Route("api/config")]
[Authorize]
public class ConfigController : ControllerBase
{
    private readonly ConfigService _configService;

    public ConfigController(ConfigService configService)
    {
        _configService = configService;
    }

    [HttpGet]
    public async Task<IActionResult> GetConfig()
    {
        var config = await _configService.GetConfigSafeAsync();
        return Ok(config);
    }

    [HttpPost("update")]
    public async Task<IActionResult> UpdateSection([FromBody] ConfigUpdateDto request)
    {
        // Prevent editing sensitive tokens via Dashboard
        if (request.Section == "api_keys" || 
            request.Section == "bot" || 
            request.Section == "database" || 
            request.Section == "security")
        {
            return StatusCode(403, new { ok = false, error = "Editing API keys and security tokens via dashboard is restricted" });
        }

        var ok = await _configService.UpdateSectionAsync(request.Section, request.Settings);
        if (!ok)
        {
            return BadRequest(new { ok = false, error = $"Failed to save section '{request.Section}'" });
        }

        return Ok(new { ok = true, section = request.Section, message = "Configuration saved successfully" });
    }

    [HttpPatch("features")]
    public async Task<IActionResult> PatchFeature([FromBody] FeaturePatchDto request)
    {
        var ok = await _configService.UpdateFeatureAsync(request.Feature, request.Value);
        if (!ok)
        {
            return BadRequest(new { ok = false, error = "Invalid feature key or write error" });
        }

        return Ok(new { ok = true, feature = request.Feature, value = request.Value });
    }
}
