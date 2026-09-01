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

        // Hide sensitive data (tokens, DB URIs, encryption keys, external API keys)
        if (configNode?["bot"] is JsonObject botObj && botObj["token"] != null)
        {
            botObj["token"] = "**********************";
        }
        if (configNode?["database"] is JsonObject dbObj && dbObj["mongo_uri"] != null)
        {
            dbObj["mongo_uri"] = "mongodb://**********************";
        }
        if (configNode?["security"] is JsonObject secObj && secObj["fernet_key"] != null)
        {
            secObj["fernet_key"] = "**********************";
        }
        if (configNode?["api_keys"] is JsonObject apiObj)
        {
            foreach (var key in apiObj.Select(k => k.Key).ToList())
            {
                apiObj[key] = "**********************";
            }
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
