using System.Text.Json;
using System.Text.Json.Nodes;
using API.Models.Requests;

namespace API.Services;

public class ConfigService
{
    private readonly string _configPath;

    public ConfigService(IConfiguration configuration)
    {
        // Path to config/settings.json relative to dashboard/API
        _configPath = configuration["CONFIG_PATH"] ?? "../../config/settings.json";
    }

    public async Task<JsonNode?> GetConfigSafeAsync()
    {
        if (!File.Exists(_configPath))
        {
            return new JsonObject();
        }

        var json = await File.ReadAllTextAsync(_configPath);
        var configNode = JsonNode.Parse(json);

        // Hide sensitive data like the Python API did
        if (configNode?["bot"]?["token"] != null)
        {
            configNode["bot"]["token"] = "**********************";
        }
        if (configNode?["database"]?["mongo_uri"] != null)
        {
            configNode["database"]["mongo_uri"] = "mongodb://**********************";
        }

        return configNode;
    }

    public async Task<bool> UpdateSectionAsync(string section, Dictionary<string, object> settings)
    {
        if (!File.Exists(_configPath)) return false;

        var json = await File.ReadAllTextAsync(_configPath);
        var configNode = JsonNode.Parse(json)?.AsObject();

        if (configNode == null) return false;

        if (!configNode.ContainsKey(section))
        {
            configNode[section] = new JsonObject();
        }

        var sectionNode = configNode[section]?.AsObject();
        if (sectionNode == null) return false;

        foreach (var (key, value) in settings)
        {
            sectionNode[key] = JsonValue.Create(value);
        }

        var options = new JsonSerializerOptions 
        { 
            WriteIndented = true,
            TypeInfoResolver = new System.Text.Json.Serialization.Metadata.DefaultJsonTypeInfoResolver() 
        };
        await File.WriteAllTextAsync(_configPath, configNode.ToJsonString(options));

        return true;
    }

    public async Task<bool> UpdateFeatureAsync(string feature, bool value)
    {
        return await UpdateSectionAsync("features", new Dictionary<string, object> { { feature, value } });
    }
}
